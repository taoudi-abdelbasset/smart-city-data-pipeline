#!/bin/bash

echo "Setting up Airflow connections..."

# Wait for Airflow webserver to be ready
echo "Waiting for Airflow to be ready..."
sleep 10

# Add Spark connection
docker exec airflow-scheduler airflow connections add 'spark_default' \
    --conn-type 'spark' \
    --conn-host 'spark://spark-master' \
    --conn-port '7077' \
    --conn-extra '{"queue": "default", "deploy-mode": "client"}' || echo "Connection already exists"

echo "✅ Spark connection configured!"

# List all connections
docker exec airflow-scheduler airflow connections list

echo "Done!"