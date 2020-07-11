import datetime as dt
import os

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator

default_args = {
	'owner': 'me',
	'start_date': dt.datetime(2020, 6, 22),
	'retries': 1,
	'retry_delay': dt.timedelta(seconds=60)
}

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

refresher = BashOperator(
	task_id='refresh_workflows',
	bash_command='python $file_path',
	env={'file_path': os.path.join(os.path.join(os.path.join(os.getcwd(), "dags"), "scripts"), "unpause_dag.py")},
	dag=dag
)

end = DummyOperator(
	task_id='end',
	dag=dag
)

start >> refresher >> end

