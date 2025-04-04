FROM python:3.8-slim

ENV     DEBIAN_FRONTEND noninteractive
ENV     TERM linux

# Airflow
ARG     AIRFLOW_VERSION=2.0.0
ENV     AIRFLOW_HOME=/usr/local/airflow
ENV     AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=false
ENV     KUBECTL_VERSION=v1.18.0

ENV     LANGUAGE en_US.UTF-8
ENV     LANG en_US.UTF-8
ENV     LC_ALL en_US.UTF-8
ENV     LC_CTYPE en_US.UTF-8
ENV     LC_MESSAGES en_US.UTF-8

# WORKDIR /requirements

COPY requirements.txt /requirements.txt

RUN         set -ex \
        &&  buildDeps=' \
                build-essential \
            ' \
            &&  apt-get update -yqq \
        &&  apt-get install -yqq --no-install-recommends \
                $buildDeps \
                apt-utils \
                locales \
                netcat \
                curl \ 
        &&      sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
        &&  locale-gen \
        &&  update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
        &&  useradd -ms /bin/bash -d ${AIRFLOW_HOME} airflow \
	&&  pip install SQLAlchemy==1.3.23 \
	&&  pip install Flask-SQLAlchemy==2.4.4 \
        &&  pip3 install -r /requirements.txt \
	&&  pip install apache-airflow-providers-amazon \
        &&  apt-get remove --purge -yqq $buildDeps libpq-dev \
        &&  apt-get clean \
        &&  rm -rf \
                /var/lib/apt/lists/* \
                /tmp/* \
                /var/tmp/* \
                /usr/share/man \
                /usr/share/doc \
                /usr/share/doc-base

# RUN     curl -L -o /usr/local/bin/kubectl \
#                https://storage.googleapis.com/kubernetes-release/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl \
#        &&  chmod +x /usr/local/bin/kubectl

COPY    ./dags ${AIRFLOW_HOME}/dags
# COPY    script/entrypoint.sh ${AIRFLOW_HOME}/entrypoint.sh

COPY    script/entrypoint-Neil.sh ${AIRFLOW_HOME}/entrypoint.sh
COPY    config/airflow.cfg ${AIRFLOW_HOME}/airflow.cfg

RUN     mkdir ${AIRFLOW_HOME}/plugins
# ADD   ./plugins ${AIRFLOW_HOME}/plugins

RUN     chown -R airflow: ${AIRFLOW_HOME} \
        &&  chmod +x ${AIRFLOW_HOME}/entrypoint.sh

EXPOSE  8080 5555 8793

USER    airflow

WORKDIR ${AIRFLOW_HOME}

ENTRYPOINT ["./entrypoint.sh"]
