import datetime as dt
import os

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from airflow.models import DagModel
from airflow.operators.python_operator import PythonOperator
from airflow.settings import Session

default_args = {
	'owner': 'me',
	'start_date': dt.datetime(2020, 6, 22),
	'retries': 1,
	'retry_delay': dt.timedelta(seconds=60)
}


def test():
	session = Session()
	session.query(DagModel).update({DagModel.is_paused: True}, synchronize_session='fetch')
	session.commit()


folder_name = "dags"

dag = DAG(
	dag_id='refresh_dags',
	default_args=default_args,
	schedule_interval=None
)

start = DummyOperator(
	task_id='start',
	dag=dag
)

refresher = PythonOperator(
	task_id='refresh_workflows',
	python_callable=test,
	provide_context=True,
	dag=dag
)

end = DummyOperator(
	task_id='end',
	dag=dag
)

start >> refresher >> end
