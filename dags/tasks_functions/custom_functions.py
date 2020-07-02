import os

import requests
from airflow.models import Variable
from dags.zeus.utils import create_request


def customized_function(**kwargs):
	"""
	
	# NOT TESTED
	
	# TODO maintain environment versions
	
	:param kwargs:
	:return:
	"""
	
	# get all the task information
	task_info = kwargs.get('template_dict').get('task_info', None)
	
	# check the type
	if task_info.get('type') == "api":
		task_instance = kwargs['ti']
		# transform_type, input & output keys will be empty
		
		# pull data from parent task(s)
		complete_data = task_instance.xcom_pull(task_ids=task_info.get('parent_task'))
		
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
		
		# TODO check response
	
	elif task_info.get('type') == "start":
		
		# get fields to be pushed in xcom
		fields = task_info.get('fields')  # dict mostly
		
		# save variables for future use
		kwargs['ti'].xcom_push(key='start', value=fields)
		
		
# def custom_function(**kwargs):
# 	"""
#
# 	Kind off completely custom, plug & play
# 	though risky
#
# 	# TODO break this func into multiple parts
# 	:params: kwargs
#
# 	# skeleton task file (build under process)
# 	{
# 		"task_name": "<name of the task>",
# 		"parent_task": [<list of parent task>]
# 		"type": "branch / http / fetch",
# 		"function_name": "custom_function",
# 		"request": {
# 			"params": [<list of params for required for current task>]
# 		},
# 		"method": "GET | POST",
# 		"child_task": [<list of task to be executed after>], - > `0` -> success task
# 		"validations": {
# 			"request": [
# 				{
# 					<possible validations on the keys mentioned in the request.params>
# 				}
# 			],
# 			"response": [
# 				{
#
# 				}
# 			],
# 		},
# 		"response": {
# 			"200": [
# 				{
# 					"success": true,	// assuming a success case
# 					"response_params": {}  // will be saved by the task_name
# 					"child_task": []
# 				},
# 				{
# 					"success": true,	// assuming a reject case
# 					"response_params": {}  // will be saved by the task_name
# 					"child_task": []
# 				}
# 			],
# 			"400": [
#
# 			],
# 			"401": [
#
# 			],
# 			"500": [
# 			]
# 		},
# 		"store": {
# 			"<name of the by which will it be saved>": {
# 				"<key>": <val>
# 			}
# 		}
# 	}
#
# 	"""
#
# 	# TODO check any params are needed to be fetch from previous request / response
# 	# TODO add aws integration for mapping in future API calls in the DAG
#
# 	# get all the task information
# 	task_info = kwargs.get('template_dict').get('task_info', None)
#
# 	# get the list of params for the request (type list)
# 	params = task_info.get('request').get('params', None)
#
# 	# type check -> http | data store
# 	type = task_info.get('type')
#
# 	try:
# 		# override params passed in the request (type dict)
# 		params = kwargs.get('dag_run').conf.get('request').get('params')
# 	except Exception as e:
# 		print(e)  # -> flow is being declared
#
# 	if type == "HTTP":
# 		# assume method & url is present in the task_info
# 		method = task_info.get('method')
#
# 		# get the environment defined in the dockerfile
# 		env = os.environ.get('env', 'dev')
#
# 		# get the url and headers from the airflow UI
# 		url = Variable.get(task_info('base_url') + "_" + env, '') + task_info.get('url')
# 		headers = Variable.get(task_info('headers') + "_" + env, {})
#
# 		# damn gotta handle request validation too
#
# 		try:
# 			if method == "GET":
# 				response = requests.get(url=url, headers=headers)
#
# 			else:
# 				# check if the data is needed to be passed in form-type or json
# 				if task_info.get('send_type') == 'json':
# 					response = requests.post(url=url, headers=headers, json=params)
# 				else:  # form-data
# 					response = requests.post(url=url, headers=headers, data=params)
#
# 			# TODO make much modular
# 			# test sample
# 			accepted_status_codes = task_info.get('response').get('success_codes', 200)
#
# 			if response.status_code in accepted_status_codes:
# 				# TODO configure dynamically
#
# 				# call child task
# 				return task_info.get('child_task')[0]
#
# 			elif response.status_code == 401:
# 				raise ValueError('forcing retry')  # test
#
# 			elif response.status_code == 500:
# 				return task_info.get('child_task')[-1]
#
# 		except Exception as e:
# 			print(e)
# 			# exception kind of too broad
# 			# TODO Throw alert
# 			raise ValueError('force retry')
#
# 	elif type == "FETCH":
# 		# TODO
# 		pass
#
# 	# save variables temporarily
# 	kwargs['ti'].xcom_push(key='', value='')
