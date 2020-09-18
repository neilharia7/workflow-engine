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
			
	class Url:
		base_url = "http://a78e1a873bab34503980b9c082cb9e41-62c6c349b3949474.elb.ap-south-1.amazonaws.com"
		version = "/v1"
		
		# endpoints
		get_constraints = base_url + version + "/poc/getConstraints"
		fetch_alert = base_url + version + "/poc/fetchAlert"
		
		# workflow triggers
		sun_pharma = base_url + version + "/workflow/trigger/sun_pharma_testing"

