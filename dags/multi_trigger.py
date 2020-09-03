import datetime as dt
import json

import requests
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from time import sleep

default_args = {
	'owner': 'neilharia7',
	'start_date': dt.datetime(2020, 9, 1),
	'retries': 1,
	'retry_delay': 30
}

dag = DAG(
	dag_id="multiDagTrigger",
	default_args=default_args,
	schedule_interval=None
)


def alert_samples(**context):
	# get the url, parameters, looping_limit
	# currently defined specifically for sun_pharma POC
	parameters = context['dag_run'].conf['params']
	
	url = "http://13.233.114.63:7070/poc/fetch_data"
	payload = {"alerts_path": parameters.get('path')}
	headers = {"Content-Type": "application/json"}
	response = requests.post(url, data=json.dumps(payload), headers=headers)
	print(f"response {response}")
	
	resp = json.loads(response.text)
	x = [k for k, v in resp.items()]
	print(x)
	
	url = "http://13.233.114.63:7070/workflow/trigger/test102"
	counter = 1
	while counter <= resp.get('iterations', 5):
		resp['row_number'] = counter
		
		# temp = {"row_number": counter}
		sleep(5)  # to handle connection resets
		response = requests.post(url, headers=headers, data=json.dumps(resp))
		print(response)
		print(response.text)
		counter += 1


start = DummyOperator(
	task_id='start',
	dag=dag
)

looping = PythonOperator(
	task_id='looping_alert_samples',
	python_callable=alert_samples,
	provide_context=True,
	do_xcom_push=True,
	dag=dag
)

end = DummyOperator(
	task_id='end',
	dag=dag
)

start >> looping >> end
