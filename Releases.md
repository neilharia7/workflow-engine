# Releases

## v1.0.11 (Latest build)  
#### Release    -   2020-09-12
#### Changes
*   Airflow Scheduler fix
    *   more like **upgrade** >> 10-20x faster execution and previous build (performance)
*   Additional Support for Business Logic 
    *   split string, mixed characters check
    
## v1.0.10 
#### Release    -   2020-09-07
#### Changes

*   Migration from Mysql to Postgres
    *   MySQL has an X-com limit of `64Kb` that causes problems when dealing 
    with large amounts of data to be tranferred between two tasks in a DAG 
    (though ideally not recommendedto do via X-com).
    On the other hand postgres supports upto `1GB` 
    (practically more but being limited in airflow) of data store per cell 
    making it the choice for the replacement.
*   Additional Support for Business Logic
    *   date conversion, 

## v1.0.9


