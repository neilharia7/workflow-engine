# This script creates DAGs in airflow dynamically by reading the customized json data from S3 bucket (transformed
# from the designer json, created while composing the workflow)

# NOTE
# Trigger rules for Airflow
# The default value for trigger_rule is all_success and can be defined as
# “trigger this task when all directly upstream tasks have succeeded”.
# All other rules described here are based on direct parent tasks and are values that can be passed to any operator
# while creating tasks:

# all_success: (default) all parents have succeeded
# all_failed: all parents are in a failed or upstream_failed state
# all_done: all parents are done with their execution
# one_failed: fires as soon as at least one parent has failed, it does not wait for all parents to be done
# one_success: fires as soon as at least one parent succeeds, it does not wait for all parents to be done
# none_failed: all parents have not failed (failed or upstream_failed) i.e. all parents have succeeded or been skipped
# none_failed_or_skipped: all parents have not failed (failed or upstream_failed) and at least one parent has succeeded.
# none_skipped: no parent is in a skipped state, i.e. all parents are in a success, failed, or upstream_failed state
# dummy: dependencies are just for show, trigger at will
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


def number_of_keys(obj):
	"""
	# check if the number of keys are greater than 1
	:param obj:
	:return:
	"""
	if isinstance(obj, dict):
		return True if len([k for k, v in obj.items()]) > 1 else False
	
	if isinstance(obj, list):
		return True if len(obj) > 1 else False


def dynamic_task_composer(task_data: dict, __dag__: dict):
	"""

	:param task_data:
	:param __dag__:
	:return:
	"""
	
	if task_data.get('type') == "start":
		# will be present in every dag composed at the start as the name suggests
		
		return PythonOperator(
			task_id=task_data.get('task_name'),
			# provide_context (bool) – if set to true,
			# Airflow will pass a set of keyword arguments that can be used in your function.
			# This set of kwargs correspond exactly to what you can use in your jinja templates.
			# For this to work, you need to define **kwargs in your function header.
			provide_context=True,
			python_callable=customized_function,
			do_xcom_push=True,  # to push the data in x-com, which can be used in subsequent tasks called
			op_kwargs=task_data.get('request'),  # optional request parameters if specified in the designer
			templates_dict={"task_info": task_data},
			# passes all the necessary information required to execute the task
			dag=__dag__
		)
	
	elif task_data.get('type') == "webhook_reject" or task_data.get('task_name') == 'error':
		
		return PythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=customized_function,
			# task will be trigger when all preceding task(s) have been executed
			trigger_rule=Config.Triggers.all_done,
			op_kwargs=task_data.get('request'),
			#  depends_on_past (boolean) that, when set to True,
			#  keeps a task from getting triggered if the previous schedule for the task hasn’t succeeded.
			depends_on_past=True,
			templates_dict={"task_info": task_data},
			do_xcom_push=True,
			dag=__dag__
		)
	
	elif task_data.get('type') in ["api", "decision"]:
		
		if number_of_keys(task_data.get('child_task', list())):
			# Branch operator as the task contains more than one child nodes
			return BranchPythonOperator(
				task_id=task_data.get('task_name'),
				provide_context=True,
				python_callable=customized_function,
				trigger_rule=Config.Triggers.one_success,
				op_kwargs=task_data.get('request'),
				depends_on_past=True,
				templates_dict={
					"task_info": task_data,
				},
				do_xcom_push=True,
				dag=__dag__
			)
		
		elif 'end' in task_data.get('child_task', list()):
			
			# Its a redundancy code, but I forgot why I seperated it in the first place,
			# also, if it works, don't touch!.
			return PythonOperator(
				task_id=task_data.get('task_name'),
				provide_context=True,
				python_callable=customized_function,
				trigger_rule=Config.Triggers.one_success,
				depends_on_past=True,
				op_kwargs=task_data.get('request'),
				templates_dict={"task_info": task_data},
				do_xcom_push=True,
				dag=__dag__
			)
		
		else:
			return PythonOperator(
				task_id=task_data.get('task_name'),
				provide_context=True,
				python_callable=customized_function,
				# this may be a concern considering dynamic DAGs is being created
				trigger_rule=Config.Triggers.one_success,
				op_kwargs=task_data.get('request'),
				depends_on_past=True,
				templates_dict={"task_info": task_data},
				do_xcom_push=True,
				dag=__dag__
			)
	
	elif task_data.get('type') == 'utility':
		# task related to all the data transformations (i.e. concat, split (upcoming.. ))
		return PythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=eval(task_data.get("transform_type")),
			do_xcom_push=True,
			trigger_rule=Config.Triggers.one_success,
			templates_dict={"task_info": task_data},
			dag=__dag__
		)
	
	elif task_data.get("type") in ["utilityDateConversion", "utilitySplitString"]:
		
		return PythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=customized_function,
			do_xcom_push=True,
			trigger_rule=Config.Triggers.one_success,
			templates_dict={"task_info": task_data},
			dag=__dag__
		)
	
	elif task_data.get('type') == "webhook_success" or task_data.get('task_name') == 'success':
		
		return PythonOperator(
			task_id=task_data.get('task_name'),
			provide_context=True,
			python_callable=customized_function,
			trigger_rule=Config.Triggers.one_success,
			op_kwargs=task_data.get('request'),
			depends_on_past=True,
			templates_dict={
				"task_info": task_data,
			},
			do_xcom_push=True,
			dag=__dag__
		)
	
	elif task_data.get('type') == 'end':
		
		return DummyOperator(
			task_id=task_data.get('task_name'),
			trigger_rule=Config.Triggers.all_done,
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
				schedule_interval=dag_data.get('scheduler', None)
		) as dag:
			
			# reverse mapping
			data_list = dag_data.get('data', list())[::-1]
			
			task_register = [dynamic_task_composer(task_data, dag) for task_data in data_list]
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
