class Config:
	
	class TaskRegistry:
		start = "start"
		
	class Triggers:
		one_success = "one_success"
		all_done = "all_done"
		
	class AWS:
		class S3:
			bucket_name = "flowxpert"
			key_path = "airflow_dag_registry/airflow_dags.json"
