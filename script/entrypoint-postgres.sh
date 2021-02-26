#!/usr/bin/env bash

CMD="airflow"
TRY_LOOP="${TRY_LOOP:-10}"
POSTGRES_HOST="${POSTGRES_HOST:-flowxpert-airflow.crhcifgoezvo.ap-south-1.rds.amazonaws.com}"
POSTGRES_PORT=5432
POSTGRES_CREDS="${POSTGRES_CREDS:-postgres:postgres12345}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres12345}"
POSTGRES_DB="${POSTGRES_DB:-airflow}"
RABBITMQ_HOST="${RABBITMQ_HOST:-rabbitmq}"
RABBITMQ_CREDS="${RABBITMQ_CREDS:-airflow:airflow}"
RABBITMQ_MANAGEMENT_PORT=15672
FLOWER_URL_PREFIX="${FLOWER_URL_PREFIX:-}"
AIRFLOW_URL_PREFIX="${AIRFLOW_URL_PREFIX:-}"
LOAD_DAGS_EXAMPLES="${LOAD_DAGS_EXAMPLES:-false}"
AIRFLOW__CORE__REMOTE_LOGGING=true
AIRFLOW__CORE__REMOTE_BASE_LOG_FOLDER="s3://flowxpert/airflow_logs"

if [[ -z ${FERNET_KEY} ]]; then
	FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; FERNET_KEY = Fernet.generate_key().decode(); print(FERNET_KEY)")
fi

echo "POSTGRES HOST: " ${POSTGRES_HOST}
echo "RABBITMQ HOST: " ${RABBITMQ_HOST}
echo "LOAD DAG EXAMPLES: " ${LOAD_DAGS_EXAMPLES}
echo "AIRFLOW HOME: " ${AIRFLOW_HOME}

# Generate Fernet key
sed -i "s/{{ FERNET_KEY }}/${FERNET_KEY}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ POSTGRES_HOST }}/${POSTGRES_HOST}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ POSTGRES_CREDS }}/${POSTGRES_CREDS}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ POSTGRES_DB }}/${POSTGRES_DB}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ RABBITMQ_HOST }}/${RABBITMQ_HOST}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ RABBITMQ_CREDS }}/${RABBITMQ_CREDS}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ LOAD_DAGS_EXAMPLES }}/${LOAD_DAGS_EXAMPLES}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s#{{ FLOWER_URL_PREFIX }}#${FLOWER_URL_PREFIX}#" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s#{{ AIRFLOW_URL_PREFIX }}#${AIRFLOW_URL_PREFIX}#" ${AIRFLOW_HOME}/airflow.cfg

AIRFLOW__CORE__SQL_ALCHEMY_CONN="postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
AIRFLOW__CELERY__RESULT_BACKEND="db+postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

echo "SQL: " ${AIRFLOW__CORE__SQL_ALCHEMY_CONN}

export AIRFLOW__CORE__SQL_ALCHEMY_CONN \
       AIRFLOW__CELERY__RESULT_BACKEND \
       AIRFLOW__CORE__REMOTE_LOGGING \
       AIRFLOW__CORE__REMOTE_BASE_LOG_FOLDER

# wait for rabbitmq
if [[ "$1" = "webserver" ]] || [[ "$1" = "worker" ]] || [[ "$1" = "scheduler" ]] || [[ "$1" = "flower" ]] ; then
  j=0
  while ! curl -sI -u ${RABBITMQ_CREDS} http://${RABBITMQ_HOST}:${RABBITMQ_MANAGEMENT_PORT}/api/whoami |grep '200 OK'; do
    j=`expr ${j} + 1`
    if [[ ${j} -ge ${TRY_LOOP} ]]; then
      echo "$(date) - $RABBITMQ_HOST still not reachable, giving up"
      exit 1
    fi
    echo "$(date) - waiting for RabbitMQ... $j/$TRY_LOOP"
    echo "curl -sI -u ${RABBITMQ_CREDS} http://${RABBITMQ_HOST}:${RABBITMQ_MANAGEMENT_PORT}/api/whoami |grep '200 OK'"
    sleep 5
  done
fi

# wait for postgres
if [[ "$1" = "webserver" ]] || [[ "$1" = "worker" ]] || [[ "$1" = "scheduler" ]] ; then
  i=0
  while ! nc ${POSTGRES_HOST} ${POSTGRES_PORT} >/dev/null 2>&1 < /dev/null; do
    i=`expr ${i} + 1`
    if [[ ${i} -ge ${TRY_LOOP} ]]; then
      echo "$(date) - ${POSTGRES_HOST}:${POSTGRES_PORT} still not reachable, giving up"
      exit 1
    fi
    echo "$(date) - waiting for ${POSTGRES_HOST}:${POSTGRES_PORT}... $i/$TRY_LOOP"
    sleep 5
  done
  if [[ "$1" = "webserver" ]]; then
    echo "Initialize database..."
    echo "$CMD initdb"
    ${CMD} init db
    airflow users create --role Admin --username admin --password admin --firstname Neil --lastname Haria --email neilharia007@gmail.com
#    python3 ${AIRFLOW_HOME}/setup_connections.py
  fi
fi

if [ "$AIRFLOW__CORE__EXECUTOR" = "CeleryExecutor" ]; then

  case "$1" in webserver)

    exec airflow webserver
    ;;

  scheduler)
    
    exec airflow "$@"
    ;;

  worker | flower)
    
    echo ${CMD}
    exec airflow celery "$@"
    ;;

  version)
    
    exec airflow "$@"
    ;;
  *)

    # The command is something like bash, not an airflow subcommand. Just run it in the right environment.
  exec "$@"
  ;;
esac

# ${CMD} "$@"
