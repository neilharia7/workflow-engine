import os

os.environ['AIRFLOW__CORE__LOGGING_LEVEL'] = 'ERROR'
os.environ['AIRFLOW__LOGGING__LOGGING_LEVEL'] = 'ERROR'
from airflow.jobs.scheduler_job import SchedulerJob
from airflow.utils.db import create_session
from airflow.utils.net import get_hostname
import sys


with create_session() as session:
	job = session.query(SchedulerJob).filter_by(hostname=get_hostname()).order_by(
		SchedulerJob.latest_heartbeat.desc()).limit(1).first()
sys.exit(0 if job.is_alive() else 1)
