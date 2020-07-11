from airflow.models import DagModel
from airflow.settings import Session

session = Session()

session.query(DagModel).update({DagModel.is_paused: False}, synchronize_session='fetch')
session.commit()

