import datetime as dt
import json
from uuid import uuid4

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
	dag_id="POCMultiTrigger",
	default_args=default_args,
	schedule_interval=None
)


def alert_samples(**context):
	# get the url, parameters, looping_limit
	# currently defined specifically for sun_pharma POC
	parameters = context['dag_run'].conf['params']
	
	url = Config.Url.get_constraints
	payload = {"path": parameters.get('path')}
	headers = {"Content-Type": "application/json"}
	response = requests.post(url, data=json.dumps(payload), headers=headers)
	print(f"response {response}")
	
	resp = json.loads(response.text)
	resp['path'] = parameters.get('path')
	context['ti'].xcom_push(key='data', value=resp)
	

def trigger_loop(**context):
	print(context)
	
	data = context['ti'].xcom_pull(key='data')
	print(f"data >> {data}")
	counter = 1
	url = Config.Url.fetch_alert
	payload = {"path": data.get('path')}
	headers = {"Content-Type": "application/json"}
	
	unique_id = str(uuid4())
	print(f"uuid {unique_id}")
	
	# testing for now
	while counter <= 1:  # data.get('iterations')
		payload['row_number'] = counter
		response = requests.post(url, data=json.dumps(payload), headers=headers)
		
		print(response)
		print(response.text)
		
		resp = json.loads(response.text)
		resp['row_number'] = counter
		resp['path'] = data.get('path')
		resp['unique_id'] = unique_id
		
		url = Config.Url.sun_pharma
		response = requests.post(url, data=json.dumps(resp), headers=headers)
		
		print(response)
		print(response.text)
		counter += 1


start = DummyOperator(
	task_id='start',
	dag=dag
)

constraints = PythonOperator(
	task_id='fetch_constraints',
	python_callable=alert_samples,
	provide_context=True,
	do_xcom_push=True,
	dag=dag
)

looping = PythonOperator(
	task_id='trigger_loop',
	python_callable=trigger_loop,
	provide_context=True,
	do_xcom_push=True,
	dag=dag
)

end = DummyOperator(
	task_id='end',
	dag=dag
)

start >> constraints >> looping >> end
