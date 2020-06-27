import datetime as dt
import json
import os

import requests
from airflow import DAG
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator
from tasks_functions.functions import *

default_args = {
	'owner': 'neilharia7',
	'start_date': dt.datetime(2020, 6, 26),
	'retries': 1,
	'retry_delay': 30
}

# switch to current directory
current_dir = os.getcwd() + "/dags"
print("abs path")
print(os.listdir('.'))

# check if there exist a json file
file_name = None
for files in os.listdir('.'):
	if files.endswith(".json") and files != "airflow_vars.json":
		file_name = files

# Testing
file_name = 'multi_dag_json.json'

# read the contents of the file
file_path = current_dir + "/" + file_name
dag_info = json.loads(open(file_path, 'r+').read())


def age_validator(**kwargs):
	# ability to change input params (request)
	task_info = kwargs.get('templates_dict').get('task_info', None)
	
	params = task_info.get('request').get('params')
	try:
		# if passed through API, override
		params = kwargs['dag_run'].conf['request']
		params = params.get('params')
	except Exception as e:
		print(e)
		pass
	
	# TODO add logics
	partner_name = params.get('partner')
	age = params.get('age')
	
	min_age = Variable.get(partner_name + "_min_age")
	max_age = Variable.get(partner_name + "_max_age")
	
	if int(min_age) <= age <= int(max_age):
		return task_info.get('child_task')[0]  # success
	else:
		return task_info.get('child_task')[-1]  # failure


def send_webhook(**kwargs):
	task_info = kwargs.get('templates_dict').get('task_info', None)
	
	url = Variable.get('base_url') + task_info.get('url')
	method = task_info.get('method')
	headers = task_info.get('headers', {})
	
	response = requests.request(url=url, method=method, headers=headers)
	
	# TODO store response in the database
	print(response)


def pan_check(**kwargs):
	task_info = kwargs.get('templates_dict').get('task_info', None)
	params = task_info.get('request').get('params')
	
	try:
		# if passed through API, override
		params = kwargs['dag_run'].conf['request']
		params = params.get('params')
	except Exception as e:
		print(e)
	
	# TODO create request as per mapping file from S3
	payload = {"pan_number": params.get('pan_number')}
	
	url = Variable.get('base_url') + task_info.get('url')
	method = task_info.get('method')
	headers = task_info.get('headers', {})
	response = requests.request(method=method, headers=headers, url=url, data=payload)
	
	print(response)
	print(response.text)
	
	# TODO configurable
	if response.status_code == 200:
		return task_info.get('child_task')[0]  # success
	
	return task_info.get('child_task')[-1]  # failure


# TODO add custom retries configurations for each task?
def create_dynamic_task(task_data: dict, dag):
	"""

    :param task_data:
    :return:
    """
	if task_data['type'] == "branch":
		
		return BranchPythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=eval(task_data.get('function_name')),
			trigger_rule="all_done",
			op_kwargs=task_data.get('request'),
			templates_dict={
				"task_info": task_data,
			},
			do_xcom_push=True,
			dag=dag
		)
	
	elif task_data['type'] == "http":
		
		return PythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=eval(task_data.get('function_name')),
			depends_on_past=True,
			do_xcom_push=True,
			op_kwargs=task_data.get('request'),
			templates_dict={
				"task_info": task_data
			},
			trigger_rule="all_done",
			dag=dag
		)


for dag_data in dag_info.get('json_request'):
	
	# TODO get the list of dags alreay registered
	
	# register DAG
	
	dag_register = {
		'owner': default_args.get('owner'),
		'start_date': dt.datetime(2020, 6, 26),
		'retries': dag_info.get('retries', default_args.get('retries')),
		'retry_delay': dt.timedelta(seconds=30)
	}
	
	with DAG(
			dag_id=dag_data.get('dag_id'),
			default_args=dag_register,
			schedule_interval=None
	) as dag:
		
		start = DummyOperator(
			task_id='start',
			dag=dag
		)
		
		end = DummyOperator(
			task_id='end',
			dag=dag
		)
		
		# reverse mapping
		data_list = dag_data['data'][::-1]
		
		task_register = [create_dynamic_task(task_data, dag) for task_data in data_list]
		reverse_dict = {"data": data_list}
		
		task_len = len(task_register)
		
		# dynamic mapping
		for child_idx, child_info in enumerate(reverse_dict['data']):
			
			if child_info.get('parent_task'):  # check if there are any parents of this task
				for parent_idx, parent_info in enumerate(dag_data.get('data')):
					
					if parent_info.get('task_name') in child_info.get('parent_task'):
						task_register[child_idx] << task_register[task_len - parent_idx - 1]
			
			else:  # map start to orphan task
				start >> task_register[child_idx]
		
		task_register[0].set_downstream(end)
		
		globals()[dag_data.get('dag_id')] = dag

