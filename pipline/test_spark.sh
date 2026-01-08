#!/bin/bash
echo "=========================================="
echo "🧪 Testing Spark + HDFS + Airflow"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Test HDFS
echo -e "\n${BLUE}Step 1: Testing HDFS${NC}"
echo "Creating directory in HDFS..."
docker exec namenode hdfs dfs -mkdir -p /smartcity/test
# FIX: Set permissions so Spark user can write
docker exec namenode hdfs dfs -chmod -R 777 /smartcity/test
docker exec namenode hdfs dfs -ls /smartcity

# Step 2: Submit Spark job from INSIDE spark-master container
echo -e "\n${BLUE}Step 2: Running Spark job from spark-master${NC}"
docker exec spark-master /opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --deploy-mode client \
    /opt/spark-jobs/test/hello_world.py

# Step 3: Verify data in HDFS
echo -e "\n${BLUE}Step 3: Verifying data in HDFS${NC}"
echo "Files created:"
docker exec namenode hdfs dfs -ls -R /smartcity/test

# Step 4: Read sample data
echo -e "\n${BLUE}Step 4: Reading sample from HDFS${NC}"
docker exec namenode hdfs dfs -cat /smartcity/test/hello_world/*.parquet 2>/dev/null | head -n 5 || echo "Data is in Parquet format (binary)"

echo -e "\n${GREEN}=========================================="
echo "✅ Test completed!"
echo "==========================================${NC}"