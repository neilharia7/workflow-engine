import datetime as dt
import json
import os

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

default_args = {
	'owner': 'me',
	'start_date': dt.datetime(2020, 6, 22),
	'retries': 1,
	'retry_delay': dt.timedelta(seconds=60)
}

folder_name = "dags"

dag = DAG(
	dag_id='create_dag',
	default_args=default_args,
	schedule_interval=None
)


def ingest_data(**kwargs):
	dag_structure = 'dag_structure'
	
	# save the json file in the current dir
	params = kwargs['dag_run'].conf[dag_structure]
	# print(params)
	print(os.getcwd())
	
	# check if json files is already there
	current_dir = os.getcwd()
	file_name = None
	
	for files in os.listdir(os.path.join(os.path.join(current_dir, folder_name), "efs")):
		if files.endswith('.json'):
			file_name = files
			break
	
	file = current_dir + "/" + folder_name + "/efs/" 
	if file_name:
		file += file_name
		data = json.loads(open(file, 'r+').read())
		# print(data)
		
		# check if the given dag id already exist in the json file
		for idx in range(len(data[dag_structure])):
			# assuming only one flow will be registered at a time
			if data[dag_structure][idx]['dag_id'] == params[0]['dag_id']:
				del data[dag_structure][idx]
				break
		
		# overwrite dag in case else append new dag
		data[dag_structure].append(params[0])
		
		with open(file, 'w+') as f:
			f.write(json.dumps(data))
	
	else:
		file += "dag_information.json"
		with open(file, 'w+') as f:
			f.write(json.dumps({dag_structure: params}))


start = DummyOperator(
	task_id='start',
	dag=dag
)

dataDog = PythonOperator(
	task_id='ingest_data',
	python_callable=ingest_data,
	provide_context=True,
	do_xcom_push=True,
	dag=dag
)

end = DummyOperator(
	task_id='end',
	dag=dag
)

start >> dataDog >> end

