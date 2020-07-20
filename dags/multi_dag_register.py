import datetime as dt
import json
import logging
import os

from airflow import DAG
# from airflow.contrib.hooks.datadog_hook import DatadogHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator
from tasks_functions.custom_functions import customized_function
from zeus.utils import *


# def datadog_event(title, text, dag_id, task_id):
# 	hook = DatadogHook()
# 	tags = [
# 		f'dag:{dag_id}',
# 		f'task:{task_id}',
# 	]
#
# 	hook.post_event(title=title, text=text, tags=tags)
#
#
# def datadog_event_success(context, **kwargs):
# 	dag_id = context['task_instance'].dag_id
# 	task_id = context['task_instance'].task_id
# 	text = f'Airflow DAG failure for {dag_id}\n\nDAG: {dag_id}\nTasks: {task_id}'
# 	title = f'Airflow DAG success for {dag_id}'
#
# 	logging.info(title)
# 	logging.info(text)
# 	logging.info(dag_id)
# 	logging.info(task_id)
#
# 	datadog_event(title, text, dag_id, task_id)


default_args = {
	'owner': 'neilharia7',
	'start_date': dt.datetime(2020, 6, 26),
	'retries': 1,
	'retry_delay': 30
	
}
# 'on_success_callback': datadog_event,


# TODO update for custom level task retries
def create_dynamic_task(task_data: dict, __dag__):
	"""
	
	:param task_data:
	:param __dag__:
	:return:
	"""
	
	if task_data['type'] in ['start']:  # the first task that works
		
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
	
	if task_data['type'] in ['webhook_reject'] or task_data.get('task_name') == "error":
		
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
	
	elif task_data['type'] in ["decision", "api"]:
		
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
	
	elif task_data['type'] in ["webhook_success"] or task_data.get('task_name') == "success":
		
		return PythonOperator(
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
	
	elif task_data['type'] in ["utility"]:
		
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
	
	elif task_data['type'] == "end":
		
		return DummyOperator(
			task_id=task_data.get('task_name'),
			trigger_rule="all_done",
			dag=__dag__
		)


# switch to current directory
current_dir = os.getcwd()
print(os.listdir(os.path.join(os.path.join(current_dir, "dags"), "efs")))

# check if there exist a json file
file_name = None
folder = "dags"
for files in os.listdir(os.path.join(os.path.join(current_dir, folder), "efs")):
	if files.endswith(".json") and files != "airflow_vars.json":
		file_name = files
		break

print("file_name", file_name)
if file_name:
	# read the contents of the file
	file_path = current_dir + "/" + folder + "/efs/" + file_name
	dag_info = json.loads(open(file_path, 'r+').read())
	
	for dag_data in dag_info.get('dag_structure', []):
		# print(dag_data)
		
		# TODO get the list of dags already registered
		
		# register DAG
		
		dag_register = {
			'owner': default_args.get('owner'),
			'start_date': dt.datetime(2020, 6, 26),
			'retries': dag_data.get('retries', default_args.get('retries')),
			'retry_delay': dt.timedelta(seconds=dag_data.get('retry_delay', default_args.get('retry_delay'))),
			'max_retry_delay': dt.timedelta(seconds=dag_data.get('max_retry_delay', 3600)),
			'retry_exponential_backoff': dag_data.get('exponential_retry', True)
		}
		
		with DAG(
				dag_id=dag_data.get('name'),
				default_args=dag_register,
				schedule_interval=None
		) as dag:
			
			start = DummyOperator(
				task_id='initiate_workflow',
				dag=dag
			)
			
			end = DummyOperator(
				task_id='terminate_workflow',
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
						
						# connect the end node
						if not parent_info.get('child_task'):
							task_register[task_len - parent_idx - 1] >> end
				
				else:  # map start to orphan task
					start >> task_register[child_idx]
			
			# dynamic dag registration
			globals()[dag_data.get('dag_id')] = dag
