import json

import requests
from zeus.utils import *


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
	print("rule", rule)
	print("data", data)
	
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
	print("task_information", task_info)
	
	task_instance = kwargs['ti']  # getting instance of task
	
	# get all the parents of this task
	parent_tasks = task_info.get('parent_task', str())
	print("parent_task", parent_tasks)
	
	# pull data from parent task(s)
	task_data = task_instance.xcom_pull(key=None, task_ids=parent_tasks)
	
	if len(parent_tasks) == 1:
		task_data = task_data[0]
	
	else:
		temp_dict = dict()
		
		for index in range(len(task_data)):
			if isinstance(task_data[index], dict):
				temp_dict.update(task_data[index])
		task_data = temp_dict
	
	print("task_data", task_data)
	
	# type check
	if task_info.get('type') == "start":
		# get fields to be pushed in xcom
		fields = task_info.get('fields')  # dict mostly
		
		try:
			# if passed through API, override
			fields = kwargs['dag_run'].conf['request']['params']
			
			print("fields", fields)
			# format key value type in input dict
			for key, val in fields.items():
				if val:
					print(key, val)
					fields[key] = parses_to_integer(val)
			
			print("formatted from user", fields)
		
		except Exception as e:
			print("error", e)
		
		print("fields >> ", fields)
		# save variables for future use
		kwargs['ti'].xcom_push(key='start', value=fields)
	
	elif task_info.get('type') == "api":  # transform_type, input & output keys will be empty
		
		request = task_info.get('request', {})  # empty dict if no request in case of GET method
		method = task_info.get('method')
		url = task_info.get('url')
		headers = task_info.get('headers')
		
		try:
			# if passed through API, override
			user_input = kwargs['dag_run'].conf['request']['params']
			
			print("user input", user_input)
			if isinstance(user_input, dict):
				
				# format key value type in input dict
				for key, val in user_input.items():
					user_input[key] = parses_to_integer(val)
				
				task_data.update(user_input)
		
		except Exception as e:
			print(e)
		
		# format request
		try:
			request = request_formatter(request)
		except Exception as e:
			print(f"Request Format Exception -> {e}")
		
		# build request body
		payload = construct_json(request, task_data)
		print("payload", payload)
		if method == "GET":
			response = requests.get(url=url, headers=headers)
		else:
			# check if the data is needed to be passed in form-type or json
			if task_info.get('send_type', '') == 'form-data':  # TODO key not present in current request format
				response = requests.post(url=url, headers=headers, data=payload)
			else:  # json
				response = requests.post(url=url, headers=headers, json=payload)
		
		print("response status >> ", response)
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
					kwargs['ti'].xcom_push(key='response', value=json.loads(response.text))
					return resp_data.get('next_task')
				
				except Exception as e:
					print("Error >> ", e)
					raise Exception(e)
	
	elif task_info.get('type') == "decision":
		
		# get the defined logic
		queries = task_info.get('query_logic')  # list
		
		# check if decision has multiple rules
		# number of outputs will be (no of queries) + 1 (reject scenario)
		
		result_task = []
		child_tasks = task_info.get('child_task')
		print("child_task", child_tasks)
		
		try:
			child_tasks.remove(task_info.get('task_name'))
		except Exception as e:
			print("exception", e)
		
		if len(queries) == 1:
			
			flag, data = format_query(task_data, queries[0])
			
			# save the data and proceed to subsequent task
			kwargs['ti'].xcom_push(key='decision', value=data)
			if flag:
				# trigger subsequent task
				return queries[0].get('result')
			else:
				print("trigger task >> ", queries[0]['result'])
				child_tasks.remove(queries[0].get('result'))
				# return another result
				return child_tasks[0]
		
		else:
			for query in queries:
				flag, data = format_query(task_data, query)
				
				# save the data and proceed to subsequent task
				kwargs['ti'].xcom_push(key='decision', value=data)
				
				if flag:
					# trigger subsequent task
					return query.get('result')
				else:
					result_task.append(query.get('result'))
			
			return list(set(child_tasks) - set(result_task))[0]
	
	elif task_info.get('type') in ["webhook_success", "webhook_reject"]:
		return task_info.get('child_task')[0]
	
	elif task_info.get('type') == "termination":
		
		body = task_info.get('responsebody', dict())
		url = task_info.get('url', '')
		body.update(task_data)
		
		response = requests.post(url=url, json=body)
		print("termination response", response)
		
		return task_info.get('child_task')[0]
