# Setup Instructions for Airflow + Spark + HDFS

## 1. Build and Start Services

```bash
# Stop existing containers
docker-compose down

# Build the custom Airflow image
docker-compose build airflow-init airflow-webserver airflow-scheduler

# Start all services
docker-compose up -d

# Check if all services are running
docker-compose ps
```

## 2. Wait for Services to Initialize

```bash
# Wait for Airflow to initialize (2-3 minutes)
docker-compose logs -f airflow-init

# Check Airflow scheduler logs
docker-compose logs -f airflow-scheduler
```

## 3. Configure Spark Connection in Airflow

**Option A: Via UI (Recommended)**
1. Go to http://localhost:8082
2. Login: `admin` / `admin`
3. Go to **Admin → Connections**
4. Click **+** to add new connection
5. Fill in:
   - **Connection Id**: `spark_default`
   - **Connection Type**: `Spark`
   - **Host**: `spark-master`
   - **Port**: `7077`
   - **Extra**: `{"queue": "default", "deploy-mode": "client"}`
6. Click **Save**

**Option B: Via Command Line**
```bash
# Make the script executable
chmod +x setup_connections.sh

# Run it
./setup_connections.sh
```

## 4. Verify Hadoop/Spark are Available in Airflow

```bash
# Check if hdfs command works
docker exec airflow-scheduler hdfs version

# Check if spark-submit works
docker exec airflow-scheduler spark-submit --version

# Check Java
docker exec airflow-scheduler java -version
```

## 5. Test the DAG

1. Copy the DAG file:
```bash
cp spark_hello_world_simple.py airflow/dags/
```

2. Go to Airflow UI: http://localhost:8082

3. Find DAG named `spark_hello_world_simple`

4. Enable it (toggle switch)

5. Click the play button (▶) to trigger it

6. Watch the logs in each task!

## 6. Troubleshooting

### If DAG fails with "hdfs: command not found"
```bash
# Check environment variables in scheduler
docker exec airflow-scheduler env | grep HADOOP
docker exec airflow-scheduler which hdfs
```

### If Spark connection fails
```bash
# Test connection from scheduler to Spark
docker exec airflow-scheduler nc -zv spark-master 7077

# Check Spark master logs
docker-compose logs spark-master
```

### View detailed task logs
- In Airflow UI, click on the task square
- Click **Log** button
- This shows the full output!

## 7. Expected Results

When successful, you should see:
1. ✅ `create_hdfs_directory` - Creates `/smartcity/test` in HDFS
2. ✅ `run_spark_hello_world` - Runs Spark job, writes data
3. ✅ `verify_hdfs_data` - Confirms data exists

## Common Issues

### Issue: "Connection refused" to HDFS
**Solution**: Make sure namenode is running and healthy
```bash
docker-compose ps namenode
curl http://localhost:9870
```

### Issue: Spark job hangs
**Solution**: Check Spark worker has resources
```bash
docker-compose logs spark-worker
# Go to http://localhost:8888 (Spark UI)
```

### Issue: Permission denied in HDFS
**Solution**: Already handled by chmod 777, but if needed:
```bash
docker exec namenode hdfs dfs -chmod -R 777 /smartcity
```

## Viewing Results

```bash
# List files in HDFS
docker exec namenode hdfs dfs -ls -R /smartcity/test

# Check file sizes
docker exec namenode hdfs dfs -du -h /smartcity/test/hello_world

# View Spark job history
# Go to: http://localhost:8888 (Spark Master UI)
```