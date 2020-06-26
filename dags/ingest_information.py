import datetime as dt
import json
import os

from uuid import uuid4
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

default_args = {
    'owner': 'me',
    'start_date': dt.datetime(2020, 6, 22),
    'retries': 2,
    'retry_delay': dt.timedelta(seconds=30)
}

dag = DAG(
    dag_id='create_dag',
    default_args=default_args,
    schedule_interval=None
)


def ingest_data(**kwargs):
    # save the json file in the current dir
    params = kwargs['dag_run'].conf['data']
    print(params)
    print(os.getcwd())
    
    path = os.getcwd() + "/dags"
    os.chdir(path=path)
    
    with open(str(uuid4()) + ".json", 'w+') as f:
        f.write(json.dumps(params))
        
    print(os.listdir('.'))


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
