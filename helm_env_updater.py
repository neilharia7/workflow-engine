import os

import yaml

"""
This script will basically get the git version tag from the commit id and update the
version in the helm chart. Will be triggered in Jenkins pipeline
"""

data_stream = open(r'helm-chart/Chart.yaml')
data = yaml.load(data_stream, Loader=yaml.FullLoader)
print(data)

commit_id = os.popen('git rev-list --tags --date-order | head -1').read()
print(f"commit_id {commit_id}")
reference_tag = os.popen(f"git show-ref --tags | grep {commit_id}").read()
print(f"reference_tag {reference_tag}")

# cleanse
version = reference_tag.split('/')[-1].replace('v', '').replace('\n', '')
data['version'] = version
print(data)

with open('helm-chart/Chart.yaml', 'w+') as file:
	file.write(yaml.dump(data, default_flow_style=False))
