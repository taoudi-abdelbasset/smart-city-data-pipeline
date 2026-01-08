"""
Airflow DAG to run Spark Hello World - Using installed clients
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'smartcity',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 8),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

dag = DAG(
    'spark_hello_world_simple',
    default_args=default_args,
    description='Spark Hello World using hdfs and spark-submit commands',
    schedule_interval=None,
    catchup=False,
    tags=['spark', 'hdfs', 'working']
)

# Task 1: Create HDFS directory using hdfs command (now available!)
create_hdfs_dir = BashOperator(
    task_id='create_hdfs_directory',
    bash_command="""
    export HADOOP_HOME=/opt/hadoop
    export PATH=$HADOOP_HOME/bin:$PATH
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
    
    echo "Creating HDFS directory..."
    hdfs dfs -mkdir -p hdfs://namenode:8020/smartcity/test
    hdfs dfs -chmod -R 777 hdfs://namenode:8020/smartcity/test
    
    echo "Verifying directory..."
    hdfs dfs -ls hdfs://namenode:8020/smartcity/
    
    echo "✅ HDFS directory created successfully!"
    """,
    dag=dag
)

# Task 2: Submit Spark job using SparkSubmitOperator
run_spark_job = SparkSubmitOperator(
    task_id='run_spark_hello_world',
    application='/opt/spark-jobs/test/hello_world.py',
    conn_id='spark_default',
    conf={
        'spark.master': 'spark://spark-master:7077',
        'spark.submit.deployMode': 'client',
        'spark.driver.memory': '512m',
        'spark.executor.memory': '512m',
        'spark.executor.cores': '1',
    },
    env_vars={
        'HADOOP_HOME': '/opt/hadoop',
        'JAVA_HOME': '/usr/lib/jvm/java-17-openjdk-amd64',
    },
    verbose=True,
    dag=dag
)

# Task 3: Verify data in HDFS
verify_hdfs_data = BashOperator(
    task_id='verify_hdfs_data',
    bash_command="""
    export HADOOP_HOME=/opt/hadoop
    export PATH=$HADOOP_HOME/bin:$PATH
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
    
    echo "Verifying data in HDFS..."
    hdfs dfs -ls -R hdfs://namenode:8020/smartcity/test
    
    echo "Checking if hello_world directory exists..."
    if hdfs dfs -test -d hdfs://namenode:8020/smartcity/test/hello_world; then
        echo "✅ Data verified successfully!"
        hdfs dfs -du -h hdfs://namenode:8020/smartcity/test/hello_world
    else
        echo "❌ Data not found!"
        exit 1
    fi
    """,
    dag=dag
)

# Set task dependencies
create_hdfs_dir >> run_spark_job >> verify_hdfs_data