import requests
from airflow.models import Variable
import os


def custom_function(**kwargs):
	"""
	
	Plan to make kindoff completely custom, plug & play
	though risky

	# TODO break this func into multiple parts
	:params: kwargs
	"""

	# TODO check any params are needed to be fetch from previous request / response
	# TODO add aws integration for mapping in future API calls in the DAG
	
	# get all the task information
	task_info = kwargs.get('template_dict').get('task_info', None)

	# get the list of params for the request
	params = task_info.get('request').get('params', None)

	# type check -> http | data store
	type = task_info.get('type')

	try:
		# override params passed in the request
		params = kwargs.get('dag_run').conf.get('request').get('params')
	except Exception as e:
		print(e)  # -> flow is being declared

	if type == "HTTP":
		# assume method & url is present in the task_info
		method = task_info.get('method')

		# get the environment defined in the dockerfile
		env = os.environ.get('env', 'dev')

		# get the url and headers from the airflow UI
		url = Variable.get(task_info('base_url') + "_" + env, '') + task_info.get('url')
		headers = Variable.get(task_info('headers') + "_" + env, {})

		# damn gotta handle request validation too

		try:
			if method == "GET":
				response = requests.get(url=url, headers=headers)

			else:
				# check if the data is needed to be passed in form-type or json
				if task_info.get('send_type') == 'json':
					response = requests.post(url=url, headers=headers, json=params)
				else:  # form-data
					response = requests.post(url=url, headers=headers, data=params)

			# TODO make much modular
			# test sample
			accepted_status_codes = task_info.get('response').get('success_codes', 200)

			if response.status_code in accepted_status_codes:
				# TODO configure dynamically

				# call child task
				return task_info.get('child_task')[0]

			elif response.status_code == 401:
				raise ValueError('forcing retry')  # test

			elif response.status_code == 500:
				return task_info.get('child_task')[-1]

		except Exception as e:
			print(e)
			# exception kind of too broad
			# TODO Throw alert
			raise ValueError('force retry')


	elif type == "FETCH":
		# TODO
		pass
