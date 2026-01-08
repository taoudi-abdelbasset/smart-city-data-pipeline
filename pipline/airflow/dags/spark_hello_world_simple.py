from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.bash import BashOperator
from datetime import datetime

dag = DAG(
    'spark_hello_world_better',
    start_date=datetime(2026, 1, 8),
    schedule_interval=None,
    catchup=False,
)

create_hdfs_dir = BashOperator(
    task_id='create_hdfs_directory',
    bash_command='hdfs dfs -mkdir -p /smartcity/test',  # Run directly if hdfs cli is in PATH, or keep docker exec namenode
    dag=dag,
)

run_spark = SparkSubmitOperator(
    task_id='run_spark_hello_world',
    application='/opt/spark-jobs/test/hello_world.py',
    conn_id='spark_default',  # Your Spark connection
    master='spark://spark-master:7077',  # Optional if set in connection
    deploy_mode='client',  # Or 'cluster' if you want
    executor_memory='1g',
    total_executor_cores=2,
    name='hello-world-airflow',
    verbose=True,
    dag=dag,
)

create_hdfs_dir >> run_spark