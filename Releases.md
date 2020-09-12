# Releases


## v1.0.11 (Latest build)
``
## v1.0.10 
### Changes

*   2020-09-07 
>   (Migration from Mysql to Postgres)

    MySQL has an X-com limit of `64Kb` that causes problems when dealing 
    with large amounts of data to be tranferred between two tasks in a DAG 
    (though ideally not recommendedto do via X-com).
    On the other hand postgres supports upto 1GB 
    (practically more but being limited in airflow) of data store per cell 
    making it the choice for the replacement.



