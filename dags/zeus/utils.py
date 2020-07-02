# utilities module
from datetime import datetime


def change_datetime(string, old_format, new_format):
	try:
		date_obj = datetime.strptime(string, old_format)
	except Exception as e:
		raise Exception("Incorrect format specified; ", e)
	return date_obj.strftime(new_format)


def parses_to_integer(string):
	"""
	checks whether the string in a number or not
	:param string:
	:return: either int or string
	"""
	if string:
		try:
			return int(float(string))
		except ValueError:
			return string
	else:
		return ""


def create_request(request_structure: dict, masala: dict):
	"""
	
	# spice it up and add fill to your request
	
	:param request_structure:
	:param masala:
	:return:
	"""
	
	for key, value in request_structure.items():
		if isinstance(value, dict):
			request_structure[key] = create_request(value, masala)
		elif isinstance(value, list):
			request_structure[key] = []
			for item in value:
				try:
					if isinstance(item, dict):
						request_structure[key].append(create_request(item, masala))
					else:
						request_structure[key].append(masala[item] if item in masala else item)
				except Exception as e:
					print("ignore: -> " + str(e))
		else:
			if value and value in masala:
				request_structure[key] = masala[value] if parses_to_integer(masala[value]) else str(masala[value])

	return request_structure


# custom utility functions
def concat(**kwargs):
	"""
	
	:param kwargs:
	:return:
	"""
	
	# get all the task information
	task_info = kwargs.get('template_dict').get('task_info', None)
	
	task_instance = kwargs['ti']
	
	# get data from previous tasks
	complete_data = task_instance.xcom_pull(task_ids=task_info.get('parent_task'))
	
	inputs = task_info.get('input')  # list
	output_field_name = task_info.get('output')[0]
	
	# converts 200.data.First-Name -> First-Name etc
	inputs = [keys.split('.')[-1] for keys in inputs]
	
	output = ""
	
	for key, value in complete_data.items():
		if key in inputs:
			output += " " + value
		
	output.strip()

	# save the transformed response	to xcom
	kwargs['ti'].xcom_push(key=output_field_name, value=output)
