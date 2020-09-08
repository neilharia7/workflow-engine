import json
import logging

import requests
from zeus.utils import *


# TODO refactor the structure completely following DRY
def request_formatter(request_json: dict) -> dict:
	"""
	format ->

	{
		"key": {
			"type": "<static / map  >",
			"value": "<value>"
	}


	:param request_json:
	:return:
	"""
	
	for key, val in request_json.items():
		request_json[key] = val.get('value')
	return request_json


def format_query(task_data, query):
	"""

	:param task_data:
	:param query:
	:return:
	"""
	
	rule = query.get('rule')
	data = query.get('data')
	
	for key, val in task_data.items():
		data = update_nested_dict(data, key, val)
		data.update(data)
	
	print(data)
	data.update(task_data)
	
	print("formatted data", data)
	
	flag = logic_decoder(rule, data)
	print("result >> ", flag)
	return flag, data


def customized_function(**kwargs):
	"""

	:param kwargs:
	:return:
	"""
	
	# get all the task information
	task_info = kwargs.get('templates_dict').get('task_info', None)
	logging.info(f"Task Information\n {task_info}")
	
	task_instance = kwargs['ti']  # getting instance of task
	
	# get all the parents of this task
	parent_tasks = task_info.get('parent_task', str())
	logging.info(f"Parent Tasks\n {parent_tasks}")
	
	# pull data from parent task(s)
	task_data = task_instance.xcom_pull(key=None, task_ids=parent_tasks)
	print(f"task_data {task_data}")
	
	task_data = dict_merge(task_data)
	logging.info(f"Task Data\n {task_data}")
	
	# type check
	if task_info.get('type') == "start":
		# get fields to be pushed in xcom
		fields = task_info.get('fields')  # dict mostly
		
		try:
			# if passed through API, override
			fields = kwargs['dag_run'].conf['request']['params']
			
			# format key value type in input dict
			for key, val in fields.items():
				if val:
					fields[key] = parses_to_integer(val)
		
		except Exception as e:
			logging.error(f"User Input Exception >> {e}")
		
		print("fields >> ", fields)
		# save variables for future use
		kwargs['ti'].xcom_push(key='start', value=fields)
	
	elif task_info.get('type') == "api":  # transform_type, input & output keys will be empty
		
		request = task_info.get('request', dict())  # empty dict if no request in case of GET method
		method = task_info.get('method')
		params = task_info.get('params', dict())
		url = task_info.get('url')
		headers = task_info.get('headers', dict())
		
		# static, dynamic header mapping check
		# TODO add mapping functionality
		for key, value in headers.items():
			if isinstance(value, dict) and value.get('type') and value.get('type') == "static":
				headers[key] = value.get("value")
		
		# TODO format the structure in classes -> production level code not adhoc
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
					user_input[key] = parses_to_integer(val)
				
				task_data.update(user_input)
				print(f'task_data\n{task_data}')
		
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
			if task_info.get('send_type', '') == 'form-data':  # TODO key not present in current request format
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
					
					print(task_info.get('task_name'))
					# TODO
					"""
					cannot pass directly the task name as key because the same cannot be used due to
					skipmixin (need to dig deeper)
					"""
					kwargs['ti'].xcom_push(key='response', value=x_com_push_data)
					return resp_data.get('next_task')
				
				except Exception as e:
					logging.error(f"Response Exception >> {e}")
					raise Exception(e)
	
	elif task_info.get('type') == "decision":
		
		# get the defined logic
		queries = task_info.get('query_logic')  # list
		
		# check if decision has multiple rules
		# number of outputs will be (no of queries) + 1 (reject scenario)
		
		result_task = []
		child_tasks = task_info.get('child_task')
		
		try:
			child_tasks.remove(task_info.get('task_name'))
		except Exception as e:
			pass
		
		if len(queries) == 1:
			"""
			For single condition/query there will be only one output node, obviously!.
			In this scenario, even if the condition fails the workflow will proceed with the result being stored
			in the assinged in the `fields` variable at the time of workflow creation.
			
			P.S. not applicable in existing workflows.
			"""
			flag, data = format_query(task_data, queries[0])
			if queries[0].get('field'):
				data.update({queries[0].get('field'): flag})
			
			# save the data and proceed to subsequent task
			kwargs['ti'].xcom_push(key='decision', value=data)
			
			# TODO check if other workflows are being affected on this condition
			return task_info.get('child_task')[0]
		
		else:
			x_com_push_data = task_data
			for query in queries:
				
				flag, data = format_query(task_data, query)
				
				# save the data and proceed to subsequent task
				x_com_push_data.update(data)
				
				if flag:
					kwargs['ti'].xcom_push(key='decision', value=x_com_push_data)
					# trigger subsequent task
					return query.get('result')
				else:
					result_task.append(query.get('result'))
			
			kwargs['ti'].xcom_push(key='decision', value=x_com_push_data)
			return list(set(child_tasks) - set(result_task))[0]
	
	elif task_info.get('type') in ["webhook_success", "webhook_reject"]:
		return task_info.get('child_task')[0]
	
	elif task_info.get('type') == "termination":
		# get the body
		request_structure = task_info.get('response', dict())
		url = task_info.get('url', '')
		
		# map the status from previous task
		status = task_data.get('status')
		
		try:
			user_input = kwargs['dag_run'].conf['request']['params']
			task_data.update(user_input)
		
		except Exception as e:
			pass
		
		# remove redundant keys
		cleanup = list()
		
		# adhoc code # TODO replace
		# removes status codes from the values if the type is `map`
		# (removed at the time of creating the intrepretable dag file)
		for k, v in request_structure.items():
			if isinstance(v, dict):
				for k1, v1 in v.items():
					v[k1] = v1.replace(k, '').strip('.') if v1.__contains__('.') else v1
		
		for key, val in request_structure.items():
			if int(status) != int(key):
				cleanup.append(key)
		for key in cleanup:
			request_structure.pop(key)
		
		for key, val in request_structure.items():
			request_structure['data'] = val
			request_structure.pop(key)
			break
		
		request_structure['run_id'] = kwargs['dag_run'].conf['run_id']
		request_structure['status_code'] = task_data.get('status')
		
		data = flatten(task_data, '', dict())
		
		print('data', data)
		payload = construct_json(request_structure, data)
		print('payload', payload)
		
		response = requests.post(url=url, json=payload)
		print("termination response", response)
		
		return task_info.get('child_task')[0]
	
	elif task_info.get('type') == "utilityDateConversion":
		
		conversion_logic = task_info.get('conversion_logic', dict())
		if conversion_logic:
			"""
			using construct_json to add date in the dictionary and converting the date
			in the new format
			"""
			updated_logic = construct_json(conversion_logic, task_data)
			
			date_variable = updated_logic.get('var')
			# None (default value) will throw error while converting and will provide a stack trace of the error
			current_date_format = updated_logic.get('currentFormat', None)
			new_date_format = updated_logic.get('expectedFormat', None)
			
			updated_date = convert_date_format(date_variable, current_date_format, new_date_format)
			
			# adding the converted date back to x_com to be used in consequent tasks
			kwargs['ti'].xcom_push(key='decision', value={task_data.get('result'): updated_date})
			
			return task_info.get('child_task')[0]
		
		else:
			raise Exception("conversion logic empty")
	
	elif task_info.get('task_name') in ['success', 'error']:
		
		url = task_info.get('url', '')
		headers = task_info.get('headers', {"Content-Type": "application/json"})
		
		# response = requests.post(url=url, headers=headers)
		return task_info.get('child_task')[0]