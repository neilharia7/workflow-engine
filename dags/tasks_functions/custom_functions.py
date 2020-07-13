import json

import requests
from zeus.utils import logic_decoder, construct_json, update_nested_dict


def customized_function(**kwargs):
	"""
	
	# TODO maintain environment versions
	
	:param kwargs:
	:return:
	"""
	
	# get all the task information
	task_info = kwargs.get('templates_dict').get('task_info', None)
	print("task_info")
	print(task_info)
	# check the type
	if task_info.get('type') == "api":
		task_instance = kwargs['ti']
		# transform_type, input & output keys will be empty
		
		# get the total number of parents
		parent_tasks = task_info.get('parent_task')
		print("parent_task", parent_tasks)
		
		# pull data from parent task(s)
		complete_data = task_instance.xcom_pull(key=None, task_ids=parent_tasks)
		print("complete data")
		print(complete_data)
		
		if len(parent_tasks) == 1:
			complete_data = complete_data[0]
		
		else:
			temp_dict = dict()
			
			# assuming tuple of dict
			for idx in range(len(complete_data)):
				if isinstance(complete_data[idx], dict):
					temp_dict.update(complete_data[idx])
			
			complete_data = temp_dict
		
		request = task_info.get('request', {})  # empty dict if no request in case of GET method
		method = task_info.get('method')
		url = task_info.get('url')
		headers = task_info.get('headers')
		
		# will be removed
		try:
			# if passed through API, override
			user_input = kwargs['dag_run'].conf['request']['params']
			print("user input", user_input)
			if isinstance(user_input, dict):
				complete_data.update(user_input)
		except Exception as e:
			print(e)
		
		# build request body
		payload = construct_json(request, complete_data)
		
		print("payload", payload)
		if method == "GET":
			response = requests.get(url=url, headers=headers)
		else:
			# check if the data is needed to be passed in form-type or json
			if task_info.get('send_type', '') == 'form-data':  # TODO key not present in current request format
				response = requests.post(url=url, headers=headers, data=payload)
			else:  # json
				response = requests.post(url=url, headers=headers, json=payload)
		
		print("response", response)
		response_structure = task_info.get('response')
		
		for status, resp_data in response_structure.items():
			if response.status_code == int(status):
				
				# check if all keys are present as expected in response
				try:
					
					# if set(json.loads(response.text)) == set(resp_data):
					# 	# save the response and proceed to subsequent task
					# 	kwargs['ti'].xcom_push(key='response', value=json.loads(response.text))
					
					# no clue whether its response.text or response.json()
					# TODO get clue
					print(response.text)
					kwargs['ti'].xcom_push(key='response', value=json.loads(response.text))
					
					return resp_data.get('next_task')
				
				except Exception as e:
					print(e)
					raise Exception(e)
	
	elif task_info.get('type') == "start":
		
		# get fields to be pushed in xcom
		fields = task_info.get('fields')  # dict mostly
		
		try:
			# if passed through API, override
			fields = kwargs['dag_run'].conf['request']['params']
		except Exception as e:
			print(e)
		
		# save variables for future use
		kwargs['ti'].xcom_push(key='start', value=fields)
	
	elif task_info.get('type') == "decision":
		
		task_instance = kwargs['ti']
		
		# get the total number of parents
		parent_tasks = task_info.get('parent_task')
		
		complete_data = task_instance.xcom_pull(key=None, task_ids=parent_tasks)
		
		if len(parent_tasks) == 1:
			complete_data = complete_data[0]
		
		else:
			temp = complete_data[0]  # dict hopefully
			
			# assuming tuple of dict
			for idx in range(1, len(complete_data)):
				
				if isinstance(complete_data[idx], dict):
					temp.update(complete_data[idx])
				else:
					print("unable to update")
					print("val", complete_data[idx])
			
			complete_data = temp
		
		# get the rule(s)
		queries = task_info.get('query_logic')  # list
		
		# check if decision has multiple rules
		# number of outputs will be (no of queries) + 1 (reject scenario)
		
		result_task = []
		child_tasks = task_info.get('child_task')
		print("child_task", child_tasks)
		# temp test
		try:
			child_tasks.remove(task_info.get('task_name'))
		except Exception as e:
			print("exception", e)
		
		# TODO implement DRY (optimize)
		if len(queries) == 1:  # outputs -> 2
			
			rule = queries[0].get('rule')
			data = queries[0].get('data')
			
			# data.update(complete_data)
			
			print("complete_data", complete_data)
			for key, val in complete_data.items():
				data = update_nested_dict(data, key, val)
				data.update(data)
			
			data.update(complete_data)
			print("data", data)
			print("query", queries)
			result = logic_decoder(rule, data)
			print("res", result)
			
			print("data", data)
			
			# save the data and proceed to subsequent task
			kwargs['ti'].xcom_push(key='decision', value=data)
			if result:
				# trigger subsequent task
				return queries[0].get('result')
			
			else:
				print("res", queries[0]['result'])
				child_tasks.remove(queries[0].get('result'))
				# return another result
				return child_tasks[0]
		
		else:
			for rule_info in queries:
				
				rule = rule_info.get('rule')
				data = rule_info.get('data')
				
				print("complete_data", complete_data)
				for key, val in complete_data.items():
					data = update_nested_dict(data, key, val)
					data.update(data)
				
				data.update(complete_data)
				
				print("rule", rule)
				print("data", data)
				
				print("res", logic_decoder(rule, data))
				
				# save the data and proceed to subsequent task
				kwargs['ti'].xcom_push(key='decision', value=data)
				
				if logic_decoder(rule, data):
					print("data", data)
					print("rule_info", rule_info)
					
					# trigger subsequent task
					return rule_info.get('result')
				else:
					result_task.append(rule_info.get('result'))
			
			return list(set(child_tasks) - set(result_task))[0]
	
	elif task_info.get('type') in ["webhook_success", "webhook_reject"]:
		return task_info.get('child_task')[0]

