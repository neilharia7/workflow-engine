from airflow.models import Variable
import requests


def age_validator(**kwargs):
    # ability to change input params (request)
    task_info = kwargs.get('templates_dict').get('task_info', None)
    
    params = task_info.get('request').get('params')
    try:
        # if passed through API, override
        params = kwargs['dag_run'].conf['request']
        params = params.get('params')
    except Exception as e:
        print(e)
        pass
    
    # TODO add logic
    partner_name = params.get('partner')
    age = params.get('age')
    
    min_age = Variable.get(partner_name + "_min_age")
    max_age = Variable.get(partner_name + "_max_age")
    
    if int(min_age) <= age <= int(max_age):
        return task_info.get('child_task')[0]  # success
    else:
        return task_info.get('child_task')[-1]  # failure
    

def send_webhook(**kwargs):
    task_info = kwargs.get('templates_dict').get('task_info', None)
    
    url = Variable.get('base_url') + task_info.get('url')
    method = task_info.get('method')
    headers = task_info.get('headers', {})
    
    response = requests.request(url=url, method=method, headers=headers)
    
    # TODO store response in the database
    print(response)


def pan_check(**kwargs):
    task_info = kwargs.get('templates_dict').get('task_info', None)
    params = task_info.get('request').get('params')
    
    try:
        # if passed through API, override
        params = kwargs['dag_run'].conf['request']
        params = params.get('params')
    except Exception as e:
        print(e)
    
    # TODO create request as per mapping file from S3
    payload = {"pan_number": params.get('pan_number')}
    
    url = Variable.get('base_url') + task_info.get('url')
    method = task_info.get('method')
    headers = task_info.get('headers', {})
    response = requests.request(method=method, headers=headers, url=url, data=payload)
    
    print(response)
    print(response.text)
    
    # TODO configurable
    if response.status_code == 200:
        return task_info.get('child_task')[0]  # success
    
    return task_info.get('child_task')[-1]  # failure

