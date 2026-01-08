"""
Airflow DAG to run Spark Hello World Job
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'smartcity',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 8),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'spark_hello_world_simple',
    default_args=default_args,
    description='Run Spark Hello World job and write to HDFS',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['spark', 'test', 'hdfs'],
)

# Task 1: Create HDFS directory if it doesn't exist
create_hdfs_dir = BashOperator(
    task_id='create_hdfs_directory',
    bash_command='docker exec namenode hdfs dfs -mkdir -p /smartcity/test || true',
    dag=dag,
)

# Task 2: Run Spark job
run_spark_job = BashOperator(
    task_id='run_spark_hello_world',
    bash_command='''
    docker exec spark-master /opt/spark/bin/spark-submit \
      --master spark://spark-master:7077 \
      --deploy-mode client \
      --executor-memory 1G \
      --total-executor-cores 2 \
      /opt/spark-jobs/test/hello_world.py
    ''',
    dag=dag,
)

# Task 3: Verify data in HDFS
verify_hdfs = BashOperator(
    task_id='verify_hdfs_data',
    bash_command='docker exec namenode hdfs dfs -ls /smartcity/test/hello_world',
    dag=dag,
)

# Set task dependencies
create_hdfs_dir >> run_spark_job >> verify_hdfs