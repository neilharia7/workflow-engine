# utilities module
import sys
from datetime import datetime
from functools import reduce
import re


def change_datetime(string, old_format, new_format):
	try:
		date_obj = datetime.strptime(string, old_format)
	except Exception as e:
		raise Exception("Incorrect format specified; ", e)
	return date_obj.strftime(new_format)


def type_checker(string: object):
	"""
	
	:param string:
	:return:
	"""
	if string:
		# check if string is bool
		try:
			return eval(str(string))
		except (NameError, SyntaxError):
			pass
		
		# if string is number
		try:
			return int(float(string))
		except (ValueError, TypeError):
			pass
		
		return str(string)
	return string  # bool, empty dict, list etc...


def parses_to_integer(string):
	"""
	checks whether the string in a number or not
	:param string:
	:return: either int or string
	"""
	if string:
		try:
			return int(float(string))
		except (ValueError, TypeError):
			# print(e)
			return string
	else:
		return string  # bool, empty dict, list etc...


def construct_json(json_structure, masala):
	"""
	
	# spice it up and add fill to your structure
	
	:param json_structure:
	:param masala:
	:return:
	"""
	
	for key, value in json_structure.items():
		if isinstance(value, dict):
			json_structure[key] = construct_json(value, masala)
		elif isinstance(value, list):
			json_structure[key] = []
			for item in value:
				try:
					if isinstance(item, dict):
						json_structure[key].append(construct_json(item, masala))
					else:
						json_structure[key].append(masala[item] if item in masala else item)
				except Exception as e:
					print("ignore: -> " + str(e))
		else:
			if value and value in masala:
				json_structure[key] = type_checker(masala[value])
				# json_structure[key] = masala[value] if parses_to_integer(masala[value]) else str(masala[value])
	
	return json_structure


def dict_merge(data):
	"""
	Converts list of tuple of dict to dict

	:param data:
	:return:
	"""

	if len(data) == 1:
		return data[0]
	else:
		temp_dict = dict()
		# assuming tuple of dict
		for idx in range(len(data)):
			if isinstance(data[idx], dict):
				temp_dict.update(data[idx])
		return temp_dict


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

	complete_data = dict_merge(complete_data)
	print(f"complete_data {complete_data}")
	
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


def regex_match(a, b):
	"""
	never assume!.
	
	:param a: object
	:param b: regex string (assumption)
	:return:
	"""

	try:
		return True if re.match(r'{}'.format(b), str(a)) else False
	except TypeError as te:
		print(f"regex match fail >> {te}")
		return False


def element_check(a, b):
	if isinstance(b, list):
		return str(a) in b
	elif isinstance(a, list):
		return str(b) in a
	else:
		return a in b if "__contains__" in dir(b) else False


def update_nested_dict(data, key, value, skip_keys):
	for k, v in data.items():
		
		# skip data in status codes e.g. 200: {}
		"""
		TODO more info to be added
		Problem it overwrites the data completely, hence the check
		"""
		if k not in skip_keys and not str(key).isdigit():
			if key == k:
				data[k] = parses_to_integer(value)
			elif isinstance(v, dict):
				update_nested_dict(v, key, value, skip_keys)
			elif isinstance(v, list):
				for o in v:
					if isinstance(o, dict):
						update_nested_dict(o, key, value, skip_keys)
	return data


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
		"!!": (lambda a: False if a is None else True),
		"in": lambda a, b: element_check(a, b),
		"not_in": lambda a, b: True if not element_check(a, b) else False,
		"regex": lambda a, b: regex_match(a, b),
		"uppercase": lambda a: str(a).upper(),
		"lowercase": lambda a: str(a).lower(),
		"contains": lambda a, b: element_check(a, b),
		"not_contains": lambda a, b: True if not element_check(a, b) else False,
		"contains_mix_char": lambda a: True if (str(a) != str(a).lower() and str(a) != str(a).upper()) else False,
		"contains_upper_char": lambda a: True if (str(a) == str(a).upper()) else False,
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


def flatten(initial, key, resultant: dict, separator=None):
	"""
	caution:
	does not help to flatten the curve
	
	:param initial:
	:param key:
	:param resultant:
	:param separator
	:return:
	"""
	
	if not separator:
		separator = '.'
	
	if isinstance(initial, dict):
		for k in initial:
			n_key = f"{key}{separator}{k}" if len(key) > 0 else k
			flatten(initial[k], n_key, resultant, separator)
	else:
		resultant[key] = initial
	return resultant


def convert_date_format(var: str, old_format: str, new_format: str):
	"""
	check if the date is input date is proper as user is always dumb
	assuming old & new format dates are valid,
	convert the date in the required format
	"""
	try:
		datetime.strptime(str(var), old_format)
	except (TypeError, ValueError) as e:
		print(f"date format mismatch {e}")
		raise  # just `raising` instead of raise ValueError as traceback will be lost
	
	return datetime.strptime(str(var), old_format).strftime(new_format)
