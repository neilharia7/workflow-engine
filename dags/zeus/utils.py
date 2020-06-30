# utilities module
from datetime import datetime


def change_datetime(string, old_format, new_format):
    try:
        date_obj = datetime.strptime(string, old_format)
    except Exception as e:
        raise Exception("Incorrect format specified; ", e)
    return date_obj.strftime(new_format)


