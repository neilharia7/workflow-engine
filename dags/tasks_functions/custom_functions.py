import json
import logging

import requests
from zeus.utils import *


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
	
	rule = query.get('rule')
	data = query.get('data')
	
	# to prevent overwriting of updated data
	skip_keys = list()
	
	for key, value in task_data.items():
		data = update_nested_dict(data, key, value, skip_keys)
		skip_keys.append(key)
		data.update(data)
	
	# print("formatted data", data)
	
	# get the result of the logic
	flag = logic_decoder(rule, data)
	print(f"rule {rule}")
	print(f"query result >> {flag}")
	return flag


def customized_function(**kwargs):
	"""

	:param kwargs: complete information of the DAG i.e. workflow
	:return:
	"""
	
	# get all the information about the task
	task_info = kwargs.get('templates_dict').get('task_info', None)
	logging.info(f"Task Information\n {task_info}")
	
	# getting instance of task
	task_instance = kwargs['ti']
	
	# get the unique run_id (uuid generated at the time of dag execution call)
	run_id = kwargs['dag_run'].conf['run_id']
	
	# get all the parents of this task
	parent_tasks = task_info.get('parent_task', str())
	logging.info(f"Parent Tasks\n {parent_tasks}")
	
	# type of the task node
	if task_info.get('type') == "start":
		
		# pull data from parent task(s), at the start key will be None
		task_data = task_instance.xcom_pull(key=None, task_ids=parent_tasks)
		task_data = dict_merge(task_data)
		print(f"task_data {task_data}")
		
		# get the fields to be pushed in the xcom
		fields = task_info.get('fields', dict())
		print(f"starting data >> {fields}")
		
		try:
			# if passed through API, override
			fields = kwargs['dag_run'].conf['request']['params']
			print(f"fields >> {fields}")
			
			# format key value type in input dict
			for key, val in fields.items():
				if val:
					fields[key] = type_checker(val)
		except Exception as e:
			logging.error(f"User Input Exception >> {e}")
		
		print("fields >> ", fields)
		# save data -> will be used in subsequent task
		kwargs['ti'].xcom_push(key=run_id, value=fields)
	
	elif task_info.get('type') == "api":  # transform_type, input & output keys will be empty
		request = task_info.get('request', dict())  # empty dict if no request in case of GET method
		method = task_info.get('method')
		params = task_info.get('params', dict())
		url = task_info.get('url')
		headers = task_info.get('headers', dict())
		
		# pull data from parent task(s)
		task_data = task_instance.xcom_pull(key=run_id, task_ids=parent_tasks)
		task_data = dict_merge(task_data)
		print(f"task data >> {task_data}")
		
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
			request = request_formatter(request)
		except Exception as e:
			print(f"Request Format Exception -> {e}")
		
		# build request body
		print(f'request >> {request}')
		payload = construct_json(request, task_data)
		print(f'payload\n{payload}')
		
		if method == "GET":
			response = requests.get(url=url, headers=headers)
		else:
			# check if the data is needed to be passed in form-type or json
			# Future support
			if task_info.get('send_type', '') == 'form-data':
				response = requests.post(url=url, headers=headers, data=payload)
			else:  # json
				response = requests.post(url=url, headers=headers, json=payload)
		
		logging.info(f"response status >> {response}")
		response_structure = task_info.get('response')
		
		for status, resp_data in response_structure.items():
			if response.status_code == int(status):
				
				# check if all keys are present as expected in response
				try:
					# future case
					# if set(json.loads(response.text)) == set(resp_data):
					# 	# save the response and proceed to subsequent task
					# 	kwargs['ti'].xcom_push(key='response', value=json.loads(response.text))
					
					# no clue whether its response.text or response.json()
					# TODO get clue
					print("response >> ", response.text)
					x_com_push_data = json.loads(response.text)
					x_com_push_data.update(task_data)
					x_com_push_data['status'] = response.status_code
					
					kwargs['ti'].xcom_push(key=run_id, value=x_com_push_data)
					return resp_data.get('next_task')
				
				except Exception as e:
					logging.error(f"Response Exception >> {e}")
					raise
	
	elif task_info.get('type') == "decision":  # task containing all the business logic
		
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
			logging.info(f'ignoring >>{e}')
		
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
					
					# Creating different keys for same data TODO fix this in future versions
					# E.g.
					# sampleA.subsampleB (the original key) -> used in json data translation (`contstruct_json`)
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
			return list(set(child_tasks) - set(result_task))[0]
	
	elif task_info.get('type') in ["webhook_success", "webhook_reject"]:  # under construction
		return task_info.get('child_task')[0]
	
	elif task_info.get('type') == "termination":
		# pull data from parent task(s)
		task_data = task_instance.xcom_pull(key=run_id, task_ids=parent_tasks)
		task_data = dict_merge(task_data)
		
		# get the body
		request_structure = task_info.get('response', dict())
		url = task_info.get('url', '')
		
		# map the status from previous task
		status = task_data.get('status')
		
		try:
			user_input = kwargs['dag_run'].conf['request']['params']
			task_data.update(user_input)
		
		except Exception as e:
			print(e)
		
		# remove redundant keys
		cleanup = list()
		
		# adhoc code # TODO replace
		# removes status codes from the values if the type is `map`
		# (removed at the time of creating the intrepretable dag file)
		print(f"request_structure {request_structure}")
		print(f"status {status}")
		for k, v in request_structure.items():
			if isinstance(v, dict):
				for k1, v1 in v.items():
					v[k1] = v1.replace(k, '').strip('.') if v1.__contains__('.') else v1
		try:
			for key, val in request_structure.items():
				if int(status) != int(key):
					cleanup.append(key)
		except Exception as e:
			print(f'exception {e}')
			pass
		for key in cleanup:
			request_structure.pop(key)
		
		for key, val in request_structure.items():
			request_structure['data'] = val
			request_structure.pop(key)
			break
		
		request_structure['run_id'] = kwargs['dag_run'].conf['run_id']
		request_structure['status_code'] = task_data.get('status', 200)
		
		data = flatten(task_data, '', dict())
		
		print('data', data)
		payload = construct_json(request_structure, data)
		
		data_from_parent = task_info.get('data_from_parent_node', {})
		payload['data'] = filter_response(data_from_parent, payload['data'])
		
		print('payload', payload)
		
		response = requests.post(url=url, json=payload)
		print("termination response", response)
		
		return task_info.get('child_task')[0]
	
	elif task_info.get('type') == "utilitySplitString":
		# pull data from parent task(s)
		task_data = task_instance.xcom_pull(key=run_id, task_ids=parent_tasks)
		task_data = dict_merge(task_data)
		
		# split logic => None?
		# DAG fails
		split_logic = task_info.get('split_logic', dict())
		
		"""
		using construct_json to pick value of the element to be split into sub-sections
		"""
		data_variable = {'var': split_logic.get('var')}
		data_variable = construct_json(data_variable, task_data)
		aliases = split_logic.get('aliases', list())
		
		# variables containing sliced values of original element value
		updated_aliases = dict()
		position = 0
		for alias in aliases:
			
			# Creating different keys for same data TODO fix this in future versions
			# E.g.
			# sampleA.subsampleB (the original key) -> used in json data translation (`contstruct_json`)
			# subsampleB (extra key) -> will be used for populating data in queries
			# both being stored in xcom so the same can be used in future tasks accordingly
			updated_aliases[alias['aliasName'].split('.')[-1]] = str(
				data_variable['var'])[position: position + int(alias['length'])]
			updated_aliases[alias['aliasName']] = str(data_variable['var'])[position: position + int(alias['length'])]
			position += int(alias['length'])
		
		task_data.update(updated_aliases)
		# adding the converted date back to x_com to be used in consequent tasks
		kwargs['ti'].xcom_push(key=run_id, value=task_data)
	
	elif task_info.get('type') == "utilityDateConversion":
		# pull data from parent task(s)
		task_data = task_instance.xcom_pull(key=run_id, task_ids=parent_tasks)
		task_data = dict_merge(task_data)
		
		print(f"task data >> {task_data}")
		
		# conversion logic => None?
		# DAG fails
		conversion_logic = task_info.get('conversion_logic', dict())
		
		"""
		using construct_json to add date in the dictionary and converting the date
		in the new format
		"""
		updated_logic = construct_json(conversion_logic, task_data)
		
		date_variable = updated_logic.get('var')
		
		# None (default value) will throw error while converting and will provide a stack trace of the error
		current_date_format = updated_logic.get('currentFormat', None)
		new_date_format = updated_logic.get('expectedFormat', None)
		
		print(f"updated_logic >> {updated_logic}")
		updated_date = convert_date_format(date_variable, current_date_format, new_date_format)
		
		# Creating different keys for same data TODO fix this in future versions
		# E.g.
		# sampleA.subsampleB (the original key) -> used in json data translation (`contstruct_json`)
		# subsampleB (extra key) -> will be used for populating data in queries
		# both being stored in xcom so the same can be used in future tasks accordingly
		alias = [key for key, value in task_info.get('result').items()][0].split('.')[-1]
		dictionary = {alias: updated_date}
		alias = [key for key, value in task_info.get('result').items()][0]
		dictionary[alias] = updated_date
		print("date converted result >> ", str(dictionary))
		task_data.update(dictionary)
		# adding the converted date back to x_com to be used in consequent tasks
		kwargs['ti'].xcom_push(key=run_id, value=task_data)
		
		return task_info.get('child_task')[0]
	
	elif task_info.get('task_name') in ['success', 'error']:  # under construction
		
		url = task_info.get('url', '')
		headers = task_info.get('headers', {"Content-Type": "application/json"})
		
		# response = requests.post(url=url, headers=headers)
		return task_info.get('child_task')[0]
