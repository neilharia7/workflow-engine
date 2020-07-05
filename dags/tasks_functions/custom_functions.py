import json

import requests
from zeus.utils import create_request, logic_decoder


def customized_function(**kwargs):
	"""
	
	# NOT TESTED
	
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
		
		# pull data from parent task(s)
		complete_data = task_instance.xcom_pull(key=None, task_ids=task_info.get('parent_task'))
		
		request = task_info.get('request')
		method = task_info.get('method')
		url = task_info.get('url')
		headers = task_info.get('headers')
		
		# build request body
		payload = create_request(request, complete_data)
		
		if method == "GET":
			response = requests.get(url=url, headers=headers)
		else:
			# check if the data is needed to be passed in form-type or json
			if task_info.get('send_type', '') == 'form-data':  # TODO key not present in current request format
				response = requests.post(url=url, headers=headers, data=payload)
			else:  # json
				response = requests.post(url=url, headers=headers, json=payload)
		
		response_structure = task_info.get('response')
		
		for status, resp_data in response_structure.items():
			if response.status_code == int(status):
				
				# check if all keys are present as expected in response
				try:
					# no clue whether its response.text or response.json()
					# TODO get clue
					if set(json.loads(response.text)) == set(resp_data):
						# save the response and proceed to subsequent task
						kwargs['ti'].xcom_push(key='response', value=json.loads(response.text))
						
						return resp_data.get('next_data')
				except Exception as e:
					
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
				temp.update(complete_data[idx])

			complete_data = temp
		
		# get the rule(s)
		queries = task_info.get('query_logic')  # list
		
		for rule_info in queries:
			
			rule = rule_info.get('rule')
			data = rule_info.get('data')
			
			data.update(complete_data)
			
			if logic_decoder(rule, data):
				
				# trigger subsequent task
				return rule_info.get('result')

