#!/bin/bash

mkdir -p spark-jobs
mkdir -p airflow/dags airflow/logs airflow/plugins
mkdir -p grafana/dashboards grafana/datasources
sudo chmod -R 775 ./airflow/dags ./airflow/logs ./airflow/plugins