import datetime as dt
import os

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

default_args = {
	'owner': 'neilharia7',
	'start_date': dt.datetime(2020, 6, 22),
	'retries': 1,
	'retry_delay': dt.timedelta(seconds=1)
}

dag = DAG(
	dag_id='setupVars',
	default_args=default_args,
	schedule_interval=None
)

start = DummyOperator(
	task_id='start',
	dag=dag
)


def update_variables(**kwargs):
	params = kwargs['dag_run'].conf['configurations']
	print(params)
	
	for key, val in params.items():
		os.system("airflow variables -s {} {}".format(key, val))
	
	print("Setup complete")
	return "Done"


settingUpVars = PythonOperator(
	task_id='settingUpVars',
	python_callable=update_variables,
	provide_context=True,
	do_xcom_push=True,
	dag=dag
)

end = DummyOperator(
	task_id='end',
	dag=dag
)

start >> settingUpVars >> end
