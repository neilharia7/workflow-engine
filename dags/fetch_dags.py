import datetime as dt
import json

import boto3
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from tasks_functions.custom_functions import customized_function
from zeus.config import *
from zeus.utils import *

default_args = {
	'owner': 'neilharia7',
	'start_date': dt.datetime(2020, 6, 26),
	'retries': 1,
	'retry_delay': 30
}

# fetch Dags from s3 bucket
s3_client = boto3.client('s3', region_name='ap-south-1')
flag, dag_information = False, dict()
try:
	dag_information = json.loads(
		s3_client.get_object(Bucket=Config.AWS.S3.bucket_name, Key=Config.AWS.S3.key_path)['Body'].read())
	print('dag fetch complete')
	if dag_information:
		flag = True
except Exception as e:
	print(f'No dags registered {e}')


def dynamic_task_creator(task_data: dict, __dag__: dict):
	"""
	
	:param task_data:
	:param __dag__:
	:return:
	"""
	
	if task_data.get('type') == 'start':
		return PythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=customized_function,
			do_xcom_push=True,
			op_kwargs=task_data.get('request'),
			templates_dict={
				"task_info": task_data
			},
			dag=__dag__
		)
	
	elif task_data.get('type') == 'webhook_reject' or task_data.get('task_name') == 'error':
		return PythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=customized_function,
			trigger_rule="all_done",
			op_kwargs=task_data.get('request'),
			depends_on_past=True,
			templates_dict={
				"task_info": task_data,
			},
			do_xcom_push=True,
			dag=__dag__
		)
	
	elif task_data.get('type') in ['decision', 'api', 'webhook_success'] or task_data.get('task_name') == 'success':
		
		return BranchPythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=customized_function,
			trigger_rule="one_success",
			op_kwargs=task_data.get('request'),
			depends_on_past=True,
			templates_dict={
				"task_info": task_data,
			},
			do_xcom_push=True,
			dag=__dag__
		)
	
	elif task_data.get('type') == 'utility':
		
		return PythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=eval(task_data.get("transform_type")),
			do_xcom_push=True,
			trigger_rule="one_success",
			templates_dict={
				"task_info": task_data
			},
			dag=__dag__
		)
	
	elif task_data.get('type') == "utilityDateConversion":
		return PythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=customized_function,
			do_xcom_push=True,
			trigger_rule="one_success",
			templates_dict={
				"task_info": task_data
			},
			dag=__dag__
		)
	
	elif task_data.get('type') == 'end':
		
		return DummyOperator(
			task_id=task_data.get('task_name'),
			trigger_rule="all_done",
			dag=__dag__
		)


if flag:
	for dag_data in dag_information.get('dag_structure', list()):
		dag_registry = {
			'owner': default_args.get('owner'),
			'start_date': dt.datetime(2020, 6, 26),
			'retries': dag_data.get('retries', default_args.get('retries')),
			'retry_delay': dt.timedelta(seconds=dag_data.get('retry_delay', default_args.get('retry_delay'))),
			'max_retry_delay': dt.timedelta(seconds=dag_data.get('max_retry_delay', 3600)),
			'retry_exponential_backoff': dag_data.get('exponential_retry', True)
		}
		
		with DAG(
				dag_id=dag_data.get('name', dag_data.get('dag_id')),
				default_args=dag_registry,
				schedule_interval=None
		) as dag:
			
			# reverse mapping
			data_list = dag_data.get('data', list())[::-1]
			
			task_register = [dynamic_task_creator(task_data, dag) for task_data in data_list]
			reverse_dict = {"data": data_list}
			
			task_len = len(task_register)
			
			# dynamic mapping
			for child_idx, child_info in enumerate(reverse_dict['data']):
				if child_info.get('parent_task'):  # check if there are any parents of this task
					for parent_idx, parent_info in enumerate(dag_data.get('data')):
						
						if parent_info.get('task_name') in child_info.get('parent_task'):
							task_register[child_idx] << task_register[task_len - parent_idx - 1]
			
			# dynamic dag registration
			globals()[dag_data.get('dag_id')] = dag
