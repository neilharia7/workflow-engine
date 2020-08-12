from __future__ import print_function

import json
import os
import sys

from airflow import settings
from airflow.models import Connection
from sqlalchemy.orm import exc


class InitializeConnections(object):
	
	def __init__(self):
		self.session = settings.Session()
	
	def has_connection(self, conn_id):
		try:
			(
				self.session.query(Connection)
					.filter(Connection.conn_id == conn_id)
					.one()
			)
		except exc.NoResultFound:
			return False
		return True
	
	def delete_all_connections(self):
		self.session.query(Connection.conn_id).delete()
		self.session.commit()
	
	def add_connection(self, **args):
		"""
		conn_id, conn_type, extra, host, login,
		password, port, schema, uri
		"""
		self.session.add(Connection(**args))
		self.session.commit()


if __name__ == "__main__":
	bucket = os.environ.get("DEFAULT_S3_BUCKET", "flowxpert")
	
	if bucket is None:
		print("DEFAULT_S3_BUCKET is not set!")
		sys.exit(1)
	
	ic = InitializeConnections()
	
	# skip initiialization if connection exists
	if ic.has_connection(bucket):
		print("Connection '{}' present".format(bucket))
		sys.exit(0)
	
	# delete all the default connections
	print("Removing example connections")
	ic.delete_all_connections()
	
	# add default S3 connection
	print("Adding default S3 connection: {}".format(bucket))
	ic.add_connection(conn_id="aws-s3", conn_type="s3",
	                  extra=json.dumps(
		                  {"aws_access_key_id": "AKIA2YVUKFCK43DXOL43",
		                   "aws_secret_access_key": "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"}
	                  ))
