from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator
import os
import json
import datetime as dt


default_args = {
    'owner': 'me',
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


def updateVariables():
	file_path = os.getcwd() + "/dags/airflow_vars.json"

	data = json.loads(open(file_path, 'r+').read())

	for key, val in data.items():
    	    os.system("airflow variables -s {} {}".format(key, val))

	print("Setup complete")
	return "Done"


settingUpVars = PythonOperator(
	task_id='settingUpVars',
    python_callable=updateVariables,        
	dag=dag
)

end = DummyOperator(
    task_id='end',
    dag=dag
)

start >> settingUpVars >> end
