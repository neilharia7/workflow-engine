import datetime as dt

import requests
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

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
	url = parameters.get('url', '')
	headers = parameters.get('headers', dict())
	request_body = parameters.get('request_body', dict())
	iterations = parameters.get('iterations')
	counter = 1
	while counter <= iterations:
		request_body['row_number'] = counter
		
		# calls another airflow dag
		response = requests.post(url=url, headers=headers, data=request_body)
		print(response, counter)
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
