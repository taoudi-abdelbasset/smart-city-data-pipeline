# Smart City Data Pipeline - Docker Setup

## 🏗️ Architecture Overview

This Docker Compose stack provides a **production-ready Big Data pipeline** for Smart City analytics:

```
IoT Data → Kafka → Spark → HDFS/PostgreSQL → Grafana
              ↓
          Airflow (Orchestration)
```

## 📦 Components

| Service | Port | Description |
|---------|------|-------------|
| **Kafka** | 9092, 9093 | Data ingestion (4 topics: traffic, camera, air quality, parking) |
| **Zookeeper** | 2181 | Kafka coordination |
| **HDFS NameNode** | 9870 (UI), 9000 | Data Lake - metadata |
| **HDFS DataNode** | 9864 | Data Lake - storage |
| **Spark Master** | 8080 (UI), 7077 | Distributed processing |
| **Spark Worker** | 8081 (UI) | Processing execution |
| **PostgreSQL** | 5432 | Analytics database |
| **Redis** | 6379 | Real-time cache |
| **Airflow Web** | 8082 | Orchestration UI |
| **Grafana** | 3000 | Dashboards |

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install Docker & Docker Compose
sudo apt update
sudo apt install docker.io docker-compose

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. Project Structure

Create this folder structure:

```
smart-city-pipeline/
├── docker-compose.yml
├── init-db.sql
├── airflow/
│   ├── dags/
│   │   └── smart_city_pipeline.py
│   ├── logs/
│   └── plugins/
├── spark-jobs/
│   ├── traffic_batch_processing.py
│   └── hourly_analytics.py
└── grafana/
    ├── dashboards/
    └── datasources/
```

### 3. Launch Pipeline

```bash
# Create required directories
mkdir -p airflow/{dags,logs,plugins} spark-jobs grafana/{dashboards,datasources}

# Copy DAG file
cp smart_city_pipeline.py airflow/dags/

# Copy Spark jobs
cp traffic_batch_processing.py spark-jobs/

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### 4. Initialize HDFS Directories

```bash
# Access namenode container
docker exec -it namenode bash

# Create HDFS directories
hdfs dfs -mkdir -p /data/raw/traffic
hdfs dfs -mkdir -p /data/raw/air_quality
hdfs dfs -mkdir -p /data/raw/parking
hdfs dfs -mkdir -p /data/raw/camera
hdfs dfs -mkdir -p /data/processed/traffic
hdfs dfs -mkdir -p /data/analytics/traffic

# Verify
hdfs dfs -ls /data/
```

## 🔧 Usage Examples

### Kafka - Create Topics & Produce Data

```bash
# Access Kafka container
docker exec -it kafka bash

# Create topics
kafka-topics --create --topic traffic-events \
  --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

kafka-topics --create --topic air-quality-events \
  --bootstrap-server localhost:9092 --partitions 2 --replication-factor 1

# List topics
kafka-topics --list --bootstrap-server localhost:9092

# Produce test message
echo '{"sensor_id":"S001","zone":"downtown","vehicle_count":45}' | \
  kafka-console-producer --topic traffic-events --bootstrap-server localhost:9092

# Consume messages
kafka-console-consumer --topic traffic-events \
  --bootstrap-server localhost:9092 --from-beginning
```

### Spark - Submit Jobs

```bash
# Submit batch processing job
docker exec -it spark-master bash

/opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  --conf spark.sql.shuffle.partitions=10 \
  /opt/spark-jobs/traffic_batch_processing.py

# Check Spark UI: http://localhost:8080
```

### Airflow - Trigger DAG

```bash
# Access Airflow UI: http://localhost:8082
# Login: admin / admin

# Trigger DAG via CLI
docker exec -it airflow-scheduler bash
airflow dags trigger smart_city_traffic_pipeline

# Check DAG status
airflow dags list
```

### PostgreSQL - Query Analytics

```bash
# Connect to database
docker exec -it postgres psql -U smartcity -d smart_city_analytics

# Query traffic analytics
SELECT zone, AVG(avg_speed) as avg_speed, COUNT(*) as events
FROM traffic_analytics
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY zone
ORDER BY avg_speed DESC;

# Check table sizes
SELECT 
  schemaname, tablename, 
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public';
```

### HDFS - Manage Data

```bash
# Upload data to HDFS
docker exec -it namenode bash
hdfs dfs -put /tmp/traffic_data.json /data/raw/traffic/

# Read data
hdfs dfs -cat /data/raw/traffic/traffic_data.json | head -20

# Check storage usage
hdfs dfs -du -h /data/

# Delete old data
hdfs dfs -rm -r /data/processed/traffic/2024-01-01
```

## 📊 Connect to Grafana

1. Access Grafana: **http://localhost:3000**
2. Login: `admin` / `admin`
3. Add PostgreSQL data source:
   - Host: `postgres:5432`
   - Database: `smart_city_analytics`
   - User: `smartcity`
   - Password: `smartcity123`
4. Import dashboard or create new panels

## 🛠️ Troubleshooting

### Check Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f spark-master
docker-compose logs -f kafka
docker-compose logs -f airflow-scheduler

# Last 100 lines
docker-compose logs --tail=100 spark-worker
```

### Restart Services

```bash
# Restart specific service
docker-compose restart kafka

# Restart all
docker-compose down
docker-compose up -d
```

### Health Checks

```bash
# Check if services are healthy
docker-compose ps

# Test Kafka
docker exec -it kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Test HDFS
docker exec -it namenode hdfs dfsadmin -report

# Test Spark
curl http://localhost:8080

# Test PostgreSQL
docker exec -it postgres pg_isready -U smartcity
```

## 🔥 Example End-to-End Workflow

```bash
# 1. Generate sample traffic data
echo '{
  "sensor_id": "S001",
  "road_id": "R101",
  "road_type": "highway",
  "zone": "downtown",
  "vehicle_count": 45,
  "average_speed": 65.5,
  "occupancy_rate": 0.72,
  "event_time": "2025-01-09T14:30:00"
}' | kafka-console-producer --topic traffic-events --bootstrap-server localhost:9092

# 2. Consume from Kafka and write to HDFS
# (Use Spark Streaming or custom consumer)

# 3. Run batch processing
docker exec -it spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark-jobs/traffic_batch_processing.py

# 4. Query results
docker exec -it postgres psql -U smartcity -d smart_city_analytics \
  -c "SELECT * FROM traffic_analytics ORDER BY timestamp DESC LIMIT 10;"

# 5. View in Grafana
# Open: http://localhost:3000
```

## 📈 Production Recommendations

### Scale Spark Workers

```yaml
# Add more workers in docker-compose.yml
spark-worker-2:
  image: bitnami/spark:3.5.0
  environment:
    SPARK_MODE: worker
    SPARK_MASTER_URL: spark://spark-master:7077
```

### Enable Kafka Replication

```yaml
# For production, use 3+ Kafka brokers
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
```

### Backup Strategy

```bash
# Backup PostgreSQL
docker exec postgres pg_dump -U smartcity smart_city_analytics > backup.sql

# Backup HDFS
hdfs dfs -get /data/processed /backup/hdfs/
```

## 🧹 Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (⚠️ deletes all data!)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## 📚 Next Steps

1. **Deploy streaming jobs** for real-time processing
2. **Configure Grafana dashboards** for traffic visualization
3. **Add machine learning models** for traffic prediction
4. **Set up monitoring** with Prometheus
5. **Enable HTTPS** for production deployment

---

**🎯 Pipeline Status:**
- ✅ Data Ingestion (Kafka)
- ✅ Storage (HDFS + PostgreSQL)
- ✅ Processing (Spark)
- ✅ Orchestration (Airflow)
- ✅ Visualization (Grafana)

**Ready for production IoT data streams from your simulation instance!**