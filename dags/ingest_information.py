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
	# save the json file in the current dir
	params = kwargs['dag_run'].conf['dag_structure']
	print(params)
	print(os.getcwd())
	
	# check if json files is already there
	current_dir = os.getcwd()
	file_name = None
	
	for files in os.listdir(os.path.join(current_dir, folder_name)):
		if files.endswith('.json') and files != "airflow_vars.json":
			file_name = files
			break
	
	file = current_dir + "/" + folder_name + "/"
	if file_name:
		file += file_name
		data = json.loads(open(file, 'r+').read())
		data['dag_structure'].append(params[0])
		
		with open(file, 'w+') as f:
			f.write(json.dumps(data))
	
	else:
		file += "dag_information.json"
		with open(file, 'w+') as f:
			f.write(json.dumps({"dag_structure": params}))


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

