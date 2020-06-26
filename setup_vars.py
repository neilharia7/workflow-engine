import os
import json

# get variables
file_name = "airflow_vars.json"

os.system("airflow variables -e {}".format(file_name))

data = json.loads(open(file_name, 'r+').read())

for k, v in data.items():
    os.system("airflow variables -s {} {}".format(k, v))

