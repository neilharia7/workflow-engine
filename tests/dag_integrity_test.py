import unittest
from airflow.models import DagBag


class TestDagIntegrity(unittest.TestCase):

	LOAD_SECOND_THRESHOLD = 5
	
	def setup(self):
		self.dagbag = DagBag
		
	def test_import_dags(self):
		self.assertFalse(
			len(self.dagbag.import_errors),
			f"DAG Import Failure. Errors {self.dagbag.import_errors}"
		)
		
		
suite = unittest.TestLoader().loadTestsFromTestCase(TestDagIntegrity)
unittest.TextTestRunner(verbosity=2).run(suite)

