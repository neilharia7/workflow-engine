# utilities module
import sys
from datetime import datetime
from functools import reduce


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


def create_request(request_structure, masala):
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
	task_info = kwargs.get('templates_dict').get('task_info', None)
	
	print("task_info", task_info)
	task_instance = kwargs['ti']
	
	# get data from previous tasks
	complete_data = task_instance.xcom_pull(key=None, task_ids=task_info.get('parent_task'))
	
	if len(complete_data) == 1:
		complete_data = complete_data[0]
	
	else:
		temp = {}
		# assuming tuple of dict
		for idx in range(len(complete_data)):
			if isinstance(complete_data[idx], dict):
				temp.update(complete_data[idx])
		
		complete_data = temp
	
	print("complete_data", complete_data)
	
	inputs = task_info.get('input')  # dict
	output = task_info.get('output')  # dict
	
	# converts 200.data.First-Name -> First-Name etc
	inputs = [key.split('.')[-1] for key, val in inputs.items()]
	
	transform = ""
	
	for key, value in complete_data.items():
		if key in inputs:
			transform += " " + value
	
	transform = transform.strip()
	
	for key, value in output.items():
		# save the transformed response	to xcom
		kwargs['ti'].xcom_push(key=key, value={key: transform})
	
	return task_info.get('child_task')[0]


def logic_decoder(rules, data=None):
	"""
	
	:param rules:
	:param data:
	:return:
	"""
	
	if rules is None or not isinstance(rules, dict):
		return rules
	
	data = data or {}
	
	ops, values = [[key, val] for key, val in rules.items()][0]
	
	operations = {
		"==": (lambda a, b: a == b),
		"===": (lambda a, b: a is b),
		"!=": (lambda a, b: a != b),
		"!==": (lambda a, b: a is not b),
		">": (lambda a, b: a > b),
		">=": (lambda a, b: a >= b),
		"<": (lambda a, b, c=None: a < b if (c is None) else (a < b) and (b < c)),
		"<=": (lambda a, b, c=None: a <= b if (c is None) else (a <= b) and (b <= c)),
		"!": (lambda a: not a),
		"%": (lambda a, b: a % b),
		"and": (lambda *args: reduce(lambda total, arg: total and arg, args, True)),
		"or": (lambda *args: reduce(lambda total, arg: total or arg, args, False)),
		"?:": (lambda a, b, c: b if a else c),
		"log": (lambda a: a if sys.stdout.write(str(a)) else a),
		"in": (lambda a, b: a in b if "__contains__" in dir(b) else False),
		"var": (
			lambda a, not_found=None:
			reduce(
				lambda data, key: (
					data.get(key, not_found) if type(data) == dict else data[int(key)]
					if (type(data) in [list, tuple] and str(key).lstrip("-").isdigit()) else not_found),
				str(a).split("."), data
			)
		),
		"cat": (lambda *args: "".join(args)),
		"+": (
			lambda *args: reduce(lambda total, arg: total + float(arg), args, 0.0)),
		"*": (
			lambda *args: reduce(lambda total, arg: total * float(arg), args, 1.0)),
		"-": (lambda a, b=None: -a if b is None else a - b),
		"/": (lambda a, b=None: a if b is None else float(a) / float(b)),
		"min": (lambda *args: min(args)),
		"max": (lambda *args: max(args)),
		"count": (lambda *args: sum(1 if a else 0 for a in args)),
	}
	
	if ops not in operations:
		raise RuntimeError("Unrecognized operation %s" % ops)  # TODO add if occurs
	
	# Easy syntax for unary operators, like {"var": "x"} instead of strict {"var": ["x"]}
	if type(values) not in [list, tuple]:
		values = [values]
	
	# To understand recursion, you must first understand recursion!
	values = map(lambda val: logic_decoder(val, data), values)
	
	return operations[ops](*values)
