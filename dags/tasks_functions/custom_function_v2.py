import json
import logging

import requests
from dags.zeus.utils import *


def request_formatter(request_json: dict):
	"""
	static -> value being predefined
	map -> value needed to be picked up usually from the parent task(s) (available in xcom)
	Sample request format:
	{
		"key": {
			"type": "<static / map  >",
			"value": "<value>"
	}

	:param request_json:
	:return:
	"""
	for key, value in request_json.items():
		request_json[key] = value.get('value')
	return request_json


def filter_response(parent_data: dict, result: dict) -> dict:
	"""
	This func will check whether any keys are not assigned any values
	if not, will be replaced by `false` as default value
	
	:param parent_data:
	:param result:
	:return:
	:rtype: dict
	"""
	
	keys = set(parent_data.keys())
	
	for key, val in result.items():
		if val in keys:
			result[key] = False
	
	return result


def format_query(task_data: dict, query: dict):
	"""

	:param task_data:
	:param query: contains business rule, data, & result field (in which the result of the logic will be stored)
	:return:
	"""
	
	rule, data = query.get('rule'), query.get('data')
	
	# to prevent overwriting of updated data
	skip_keys = list()
	
	for key, value in task_data.items():
		data = update_nested_dict(data, key, value, skip_keys)
		skip_keys.append(key)
		data.update(data)
	
	# print("formatted data", data)
	
	# get the result of the logic
	flag = logic_decoder(rule, data)
	logging.info(f"rule {rule}\nquery result >> {flag}")
	return flag


def customized_function(**kwargs):
	"""
	
	This function acts as a separation of concerns based on the type of task
	as defined in the workflow designer
	Currently supported types
		start   -   is basically the origination of the workflow i.e. no parent tasks is gonna call this one.
					contains all the input params that the workflow requries initially to start the execution process
					:type   DummyOperator
				
		api     -   as the name suggests this task makes an external API request from the workflow to get relevant
					response as per contract defined in the API Framer while registering the API.
					AS any other API schema, there is support for query params, request body (JSON)
					Limitations:
					-   Form-data (IN development pipeline)
					-   No file upload
					-   SOAP/XML format not available
					-   maybe more that I don't recall
					:type   BranchPythonOperator
					
		decision    this is kindof the real deal, decodes the json logic and pops out result based on condition(s) being
					set by the creator of the workflow in the designer.
					:type   BranchPythonOperator
					
		webhooks    to pop out result back to the one that calls the workflow
					similar to what API task is except its reverse in nature
					Categories
					-   Success
					-   Reject
					:type   BranchPythonOperator
					
		termination mandatory requirement for every workflow, this basically updates the result of the workflow in
					the database (DynamoDB in this case) or as defined in the API that will be called.
					It's also the penultimate stage of the workflow
					Categories
					-   Success
					-   Error
					Error needs to get invoked if there is/are conditions that are not being satisfied by the input
					params passed by the user invoking the workflow.
					
		utilities   Currently
					-   utilitySplitString
						-   Breaks down string into batches as per the conditions set by the creator
					-   utilityDateConversion
						-   Converts date from one format to another
						
					Many more upcoming in the pipeline...

	:param kwargs: complete information of the DAG i.e. workflow
	:return:
	"""
	
	# get the complete information of the task at hand (type: dict)
	task_info = kwargs.get('templates_dict').get('task_info', None)
	logging.info(f"Task Information\n{task_info}")
	
	# fetch instance of the task
	task_instance = kwargs['ti']
	
	# get the unique run_id (uuid generated at the time of dag execution call)
	# this is passed by the user at the time of invoking the workflow in request body
	run_id = kwargs['dag_run'].conf['run_id']
	
	# get all the parents of this task, if any
	parent_tasks = task_info.get('parent_task', str())
	logging.debug(f"Parent Tasks\n{parent_tasks}")
	
	if task_info.get('type') == 'start':
		"""
		Sample Struct
		{
			"task_name":"start",
			"task_id":"start",
			"type":"start",
			"parent_task":[],
			"child_task":[<child_task>],
			"data_from_parent_node":[],
			"input":{},
			"output":{},
			"retries":5,
			"max_retry_delay":3600,
			"exponential_retry":true,
			"retry_delay":30,
			"fields":{
				<key>: <type>,
				...
			}
		}
		"""
	
		# get the field level mappings that will be pushed in the consequent tasks via Xcoms
		fields = task_info.get('fields', dict())
		logging.info(f"starting data >> {fields}")
		
		try:
			# if data is passed through API, override the fields
			fields = kwargs['dag_run'].conf['request']['params']
			logging.info(f"data recieved from API >> {fields}")
			
			# format key value mapping in input dictionary
			for key, val in fields.items():
				if val:
					fields[key] = type_checker(val)
		except Exception as e:
			logging.error(f"User Input Exception >> {e}")
			
		logging.debug(f"data pushed to Xcom {fields}")
		# save data -> will be used in subsequent task
		kwargs['ti'].xcom_push(key=run_id, value=fields)
		
	elif task_info.get('type') == "api":    # transform_type, input & output keys will be empty
		"""
		Sample Struct
		{
            "task_name": "<task_name>",
            "task_id": "<task_id>",
            "type": "api",
            "parent_task": [
                "<parent_task(s)>"
            ],
            "child_task": [
                "<child_tasks>",
            ],
            "data_from_parent_node": {
                "<key>": "<value>",
                "<key>": "<value>",
                .
            },
            "input": {},
            "output": {},
            "retries": 3,
            "max_retry_delay": 1200,
            "exponential_retry": false,
            "retry_delay": 600,
            "request": {
                "<key>": {
                    "type": "map",
                    "value": "<value>"
                }
            },
            "params": {},
            "headers": {
                "Content-Type": {
                    "type": "static",
                    "value": "application/json"
                },
                
            },
            "method": "<method>",
            "url": "<url>",
            "response": {
                "<status_code>": {
                    "<key>": "<value>",
                    "<key>": "<value>",
                    ...
                },
                "<status_code>": {
                    "<key>": "<value>",
                    "<key>": "<value>",
                    ...
                },
                ..
            }
        }
		"""
		
		# segragate all the data from the task_info required to call the respective API
		request_structure = task_info.get('request', dict())  # empty dict if no request in case of GET method
		method = task_info.get('method')
		params = task_info.get('params', dict())    # can be empty depending upon the URL to be called
		url = task_info.get('url')
		headers = task_info.get('headers', dict())
		
		# pull data from parent task(s)
		task_data = task_instance.xcom_pull(key=run_id, task_ids=parent_tasks)
		task_data = dict_merge(task_data)
		logging.info(f"task data >> {task_data}")
		
		# static, dynamic header mapping check
		# TODO add mapping functionality
		for key, value in headers.items():
			if isinstance(value, dict) and value.get('type') and value.get('type') == "static":
				headers[key] = value.get("value")
				
		# for GET method
		if params:
			for key, value in params.items():
				if isinstance(value, dict) and value.get('type') and value.get('type') == "static":
					params[key] = value.get('value')
			
			# removes the {} from the url and appends the value to the url
			url = url.split("{")[0] + [val for key, val in params.items()][0]
		
		try:
			# if passed through API, override
			user_input = kwargs['dag_run'].conf['request']['params']
			
			logging.info(f'User Input {user_input}')
			if isinstance(user_input, dict):
				# format key value type in input dict
				for key, val in user_input.items():
					user_input[key] = type_checker(val)
				
				task_data.update(user_input)
			# print(f'task_data\n{task_data}')
		
		except Exception as e:
			logging.error(f'User Input Exception {e}')
		
		# format request
		try:
			request_structure = request_formatter(request_structure)
		except Exception as e:
			logging.info(f"Request Format Exception -> {e}")
			
		# building request body
		logging.debug(f'request >> {request_structure}')
		payload = construct_json(request_structure, task_data)
		logging.info(f'payload\n{payload}')
		
		if method.lower() == "get":
			response = requests.get(url=url, headers=headers)
			
		else:
			# check if the data is needed to be passed in form-type or json
			# Future support
			if task_info.get('send_type', '') == 'form-data':
				response = requests.post(url=url, headers=headers, data=payload)
			else:  # json
				response = requests.post(url=url, headers=headers, json=payload)
		
		logging.info(f"response status >> {response}\nresponse body >> {response.text}")
		response_structures = task_info.get('response', dict())  # type: dict
		
		for status_code, resp_structure in response_structures.items():
			if response.status_code == int(status_code):
				# check if all keys are present as expected in response
				try:
					x_com_push_data = json.loads(response.text)
					x_com_push_data.update(task_data)
					x_com_push_data['status'] = response.status_code
					
					# adding skip tasks to eliminate possibility of consequent tasks getting triggered unnecessarily
					x_com_push_data['skipped_tasks'] = task_info.get('child_task').pop(resp_structure.get('next_task'))
					
					kwargs['ti'].xcom_push(key=run_id, value=x_com_push_data)
					# if success call the subsequent task
					return resp_structure.get('next_task')
				
				except Exception as e:
					# TODO handle this kind of cases
					logging.error(f"Response Exception >> {e}")
					raise
				
	elif task_info.get('type') == 'decision':  # task containing all the business logic
		"""
		Sample struct
		{
			"task_name": "<task_name>",
            "task_id": "<task_id>",
            "type": "api",
            "parent_task": [
                "<parent_task(s)>"
            ],
            "child_task": [
                "<child_tasks>",
            ],
			"data_from_parent_node":{
				"<key>": "<value>",
                "<key>": "<value>",
                .
			},
			"input":{},
			"output":{},
			"retries":5,
			"max_retry_delay":3600,
			"exponential_retry":true,
			"retry_delay":30,
			"query_logic":[
				{
					"rule":{
						"and":[
							{
								"!=":[
									{
										"var":"CKYC"
									},
									"Y"
								]
							}
						]
					},
					"data":{
						"CKYC":"None"
					},
					"fields":{
						"KYCCheck.OKYC":"boolean"
					},
					"result":"success"
				},
				{
					"rule":{
						"and":[
							{
								"==":[
									{
										"var":"CKYC"
									},
									"Y"
								]
							}
						]
					},
					"data":{
						"CKYC":"None"
					},
					"fields":{
						"KYCCheck.CKYC":"boolean"
					},
					"result":"EmploymentCheck"
				}
			]
		}
		"""
		# pull data from parent task(s)
		task_data = task_instance.xcom_pull(key=run_id, task_ids=parent_tasks)
		task_data = dict_merge(task_data)
		
		# get the defined logic
		queries = task_info.get('query_logic')  # list
		
		# check if decision has multiple rules
		# number of outputs will be (no of queries) + 1 (reject scenario)
		
		result_task = list()
		child_tasks = task_info.get('child_task')
		
		try:
			# removing looping condition
			child_tasks.remove(task_info.get('task_name'))
		except Exception as e:
			logging.info(f'ignoring >> {e}')
		
		if len(queries) == 1:
			"""
			For single condition/query there will be only one output node, obviously!.
			In this scenario, even if the condition fails the workflow will proceed with the result being stored
			in the assinged in the `fields` variable at the time of workflow creation.

			P.S. not applicable in existing workflows.
			"""
			flag = format_query(task_data, queries[0])
			if queries[0].get('fields'):
				# Creating different keys for same data TODO fix this in future versions
				# E.g.
				# sampleA.subsampleB (the original key) -> used in json data translation (`contstruct_json`)
				# subsampleB (extra key) -> will be used for populating data in queries
				# both being stored in xcom so the same can be used in future tasks accordingly
				key = [k for k, v in queries[0].get('fields').items()][0]
				res = {key: flag}
				key = [k for k, v in queries[0].get('fields').items()][0].split('.')[-1]
				res[key] = flag
				print(f"res update >> {res}")
				task_data.update(res)
			
			# save the data and proceed to subsequent task
			kwargs['ti'].xcom_push(key=run_id, value=task_data)
			
			return task_info.get('child_task')[0]
		
		else:
			for index, query in enumerate(queries):
				
				flag = format_query(task_data, query)
				
				# limitations -> only a single key will be updated
				if query.get('fields'):
					key = [k for k, v in query.get('fields').items()][0]
					res = {key: flag}
					
					# Creating different keys for same data
					# TODO fix this in future versions
					# E.g.
					# sampleA.subsampleB (the original key) -> used in json data translation (`construct_json`)
					# subsampleB (extra key) -> will be used for populating data in queries
					# both being stored in xcom so the same can be used in future tasks accordingly
					key = [k for k, v in query.get('fields').items()][0].split('.')[-1]
					res[key] = flag
					print(f"else res update >> {res}")
					task_data.update(res)
				
				if flag:
					kwargs['ti'].xcom_push(key=run_id, value=task_data)
					# trigger subsequent task
					return query.get('result')
				else:
					result_task.append(query.get('result'))
			
			kwargs['ti'].xcom_push(key=run_id, value=task_data)
			print(f"child_tasks {child_tasks}")
			print(f"result_task {result_task}")
			
			# TODO find out the reason behind this
			
			return list(set(child_tasks) - set(result_task))[0]
		
	elif task_info.get('type') == 'termination':
		"""
		Sample Struct
		
		{
            "task_name": "<task_name>",
	        "task_id": "<task_id>",
	        "type": "api",
	        "parent_task": [
	            "<parent_task(s)>"
	        ],
	        "child_task": [
	            "<child_tasks>",
	        ],
            "data_from_parent_node": {
	            "<key>": "<value>",
	            "<key>": "<value>",
	            .
	        },
            "input": {},
            "output": {},
            "retries": 5,
            "max_retry_delay": 3600,
            "exponential_retry": true,
            "retry_delay": 30,
            "method": "<method>",
	        "url": "<url>",
	        "response": {
	            "<status_code>": {
	                "<key>": "<value>",
	                "<key>": "<value>",
	                ...
	            },
	            "<status_code>": {
	                "<key>": "<value>",
	                "<key>": "<value>",
	                ...
	            },
	            ..
	        }
        }
		"""
		
		# pull data from parent task(s)
		task_data = task_instance.xcom_pull(key=run_id, task_ids=parent_tasks)
		task_data = dict_merge(task_data)
		
		# get the response body structure needed to be stored in dynamodb
		response_structure = task_info.get('response', dict())
		url = task_info.get('url', '')
		
		# map the status from previous task
		# NOTE: this will only be applicable if the termination is initiated by a parent node having type as `api`
		status = task_data.get('status')
		
		try:
			user_input = kwargs['dag_run'].conf['request']['params']
			task_data.update(user_input)
		
		except Exception as e:
			print(e)
			pass
		
		if status:
			# remove redundant keys
			cleanup = list()
			
			# adhoc code # TODO replace
			# removes status codes from the values if the type is `map`
			# (removed at the time of creating the intrepretable dag file)
			logging.debug(f"workflow response structure {response_structure}")
			logging.debug(f"status {status}")
			for k, v in response_structure.items():
				if isinstance(v, dict):
					for k1, v1 in v.items():
						v[k1] = v1.replace(k, '').strip('.') if v1.__contains__('.') else v1
			try:
				for key, val in response_structure.items():
					if int(status) != int(key):
						cleanup.append(key)
			except Exception as e:
				logging.error(f'exception {e}')
				pass
			for key in cleanup:
				response_structure.pop(key)
			
			for key, val in response_structure.items():
				response_structure['data'] = val
				response_structure.pop(key)
				break
			
			response_structure['status_code'] = task_data.get('status')
		
		response_structure['run_id'] = kwargs['dag_run'].conf['run_id']
		data = flatten(task_data, '', dict())
		
		logging.info(f"data {data}")
		payload = construct_json(response_structure, data)
		
		data_from_parent = task_info.get('data_from_parent_node', {})
		
		payload = filter_response(data_from_parent, payload)
		
		logging.info('payload', payload)
		
		response = requests.post(url=url, json=payload)
		logging.info("termination response", response, response.text)
		
		return task_info.get('child_task')[0]