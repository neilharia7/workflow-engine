#!/usr/bin/env bash

CMD="airflow"
TRY_LOOP="${TRY_LOOP:-10}"
MYSQL_HOST="${MYSQL_HOST:-testserver.crhcifgoezvo.ap-south-1.rds.amazonaws.com}"
MYSQL_PORT=3306
MYSQL_CREDS="${MYSQL_CREDS:-thinktest:testadmin}"
MYSQL_USER="${MYSQL_USER:-thinktest}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-testadmin}"
MYSQL_DB="${MYSQL_DB:-airflow}"
RABBITMQ_HOST="${RABBITMQ_HOST:-rabbitmq}"
RABBITMQ_CREDS="${RABBITMQ_CREDS:-airflow:airflow}"
RABBITMQ_MANAGEMENT_PORT=15672
FLOWER_URL_PREFIX="${FLOWER_URL_PREFIX:-}"
AIRFLOW_URL_PREFIX="${AIRFLOW_URL_PREFIX:-}"
LOAD_DAGS_EXAMPLES="${LOAD_DAGS_EXAMPLES:-false}"

if [[ -z ${FERNET_KEY} ]]; then
	FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; FERNET_KEY = Fernet.generate_key().decode(); print(FERNET_KEY)")
fi

echo "MYSQL HOST: " ${MYSQL_HOST}
echo "RABBITMQ HOST: " ${RABBITMQ_HOST}
echo "LOAD DAG EXAMPLES: " ${LOAD_DAGS_EXAMPLES}
echo "AIRFLOW HOME: " ${AIRFLOW_HOME}

# Generate Fernet key
sed -i "s/{{ FERNET_KEY }}/${FERNET_KEY}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ MYSQL_HOST }}/${MYSQL_HOST}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ MYSQL_CREDS }}/${MYSQL_CREDS}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ MYSQL_DB }}/${MYSQL_DB}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ RABBITMQ_HOST }}/${RABBITMQ_HOST}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ RABBITMQ_CREDS }}/${RABBITMQ_CREDS}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s/{{ LOAD_DAGS_EXAMPLES }}/${LOAD_DAGS_EXAMPLES}/" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s#{{ FLOWER_URL_PREFIX }}#${FLOWER_URL_PREFIX}#" ${AIRFLOW_HOME}/airflow.cfg
sed -i "s#{{ AIRFLOW_URL_PREFIX }}#${AIRFLOW_URL_PREFIX}#" ${AIRFLOW_HOME}/airflow.cfg

AIRFLOW__CORE__SQL_ALCHEMY_CONN="mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DB}"
# AIRFLOW__CELERY__RESULT_BACKEND="db+mysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DB}"

echo "SQL: " ${AIRFLOW__CORE__SQL_ALCHEMY_CONN}

export AIRFLOW__CORE__SQL_ALCHEMY_CONN AIRFLOW__CELERY__RESULT_BACKEND

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
  while ! nc ${MYSQL_HOST} ${MYSQL_PORT} >/dev/null 2>&1 < /dev/null; do
    i=`expr ${i} + 1`
    if [[ ${i} -ge ${TRY_LOOP} ]]; then
      echo "$(date) - ${MYSQL_HOST}:${MYSQL_PORT} still not reachable, giving up"
      exit 1
    fi
    echo "$(date) - waiting for ${MYSQL_HOST}:${MYSQL_PORT}... $i/$TRY_LOOP"
    sleep 5
  done
  if [[ "$1" = "webserver" ]]; then
    echo "Initialize database..."
    echo "$CMD initdb"
    ${CMD} initdb
  fi
fi

${CMD} "$@"