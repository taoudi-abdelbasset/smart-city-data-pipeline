# PyFlink Vision Job - Complete Guide

## What Changed? 🔄

### Old Code (kafka-python)
```python
from kafka import KafkaConsumer  # ❌ Not using Flink
consumer = KafkaConsumer(...)
for message in consumer:
    process(message)
```
- ❌ Won't show in Flink UI
- ❌ Not using Flink's engine
- ❌ No parallelization
- ❌ No fault tolerance

### New Code (PyFlink)
```python
from pyflink.datastream import StreamExecutionEnvironment  # ✅ Using Flink!
env = StreamExecutionEnvironment.get_execution_environment()
stream = env.from_source(kafka_source)
stream.map(process).print()
env.execute("Vision Job")  # ✅ Submits to Flink
```
- ✅ **Shows in Flink UI** 🎯
- ✅ Uses Flink's distributed engine
- ✅ Automatic parallelization
- ✅ Fault tolerance with checkpointing
- ✅ Managed state

## Files You Need

### 1. Place in `data-processor/stream/rtsp_process/`:
```
flink_vision_job_proper.py      ← New PyFlink job
deploy_flink_vision_job.sh      ← Deployment script
```

### 2. Update in project root:
```
Dockerfile.flink                ← Updated with all dependencies
```

## Quick Deploy

### Step 1: Copy files

```bash
cd ~/smart-city-data-pipeline/pipline2

# Create the PyFlink job
nano data-processor/stream/rtsp_process/flink_vision_job_proper.py
# Paste the code from artifact

# Create deploy script
nano data-processor/stream/rtsp_process/deploy_flink_vision_job.sh
# Paste the deploy script

# Update Dockerfile
nano Dockerfile.flink
# Paste the updated Dockerfile

# Make executable
chmod +x data-processor/stream/rtsp_process/deploy_flink_vision_job.sh
```

### Step 2: Deploy

```bash
cd data-processor/stream/rtsp_process
./deploy_flink_vision_job.sh
```

This will:
1. Copy job to `flink-jobs/`
2. Rebuild Flink containers with Python
3. Restart Flink
4. Submit the job

### Step 3: Check Flink UI

```
http://localhost:8083
```

You should see: **"Vision Processor - Object Detection & Tracking"**

## Flink Pipeline Structure

```
┌─────────────────────────────────────┐
│ Kafka Source                        │
│ Topic: smart-city-camera-frames     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ YOLO Frame Processor (MapFunction)  │
│ - Decode base64                     │
│ - Run YOLO detection                │
│ - Extract age/gender                │
│ Parallelism: 2 (distributable)      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Filter Invalid Frames               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Key By camera_id                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Object Tracker (KeyedProcessFunc)   │
│ - Stateful per camera               │
│ - Flink manages state               │
│ - Fault tolerant                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Result Printer (MapFunction)        │
│ - Print to console                  │
│ - TODO: Write to HDFS/TimescaleDB   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Console Output                      │
└─────────────────────────────────────┘
```

## Key Features

### 1. Distributed Processing
```python
env.set_parallelism(2)  # Run 2 parallel tasks
```

Flink automatically distributes work across TaskManagers!

### 2. Fault Tolerance
```python
env.enable_checkpointing(60000)  # Checkpoint every 60s
```

If a task fails, Flink restarts from last checkpoint!

### 3. Managed State
```python
class ObjectTracker(KeyedProcessFunction):
    def open(self, runtime_context):
        state_descriptor = ValueStateDescriptor(...)
        self.tracker_state = runtime_context.get_state(state_descriptor)
```

Flink manages tracker state per camera with fault tolerance!

## Monitoring

### Check if Job is Running

```bash
# Via Flink UI
http://localhost:8083

# Via command line
docker exec flink-jobmanager pgrep -f flink_vision_job_proper.py
```

### View Logs

```bash
# Job logs
docker exec flink-jobmanager tail -f /tmp/vision_job.log

# Flink logs
docker logs flink-jobmanager
docker logs flink-taskmanager
```

### Stop Job

```bash
docker exec flink-jobmanager pkill -f flink_vision_job_proper.py
```

## Differences from Old Code

| Feature | Old (kafka-python) | New (PyFlink) |
|---------|-------------------|---------------|
| Shows in UI | ❌ No | ✅ Yes |
| Uses Flink engine | ❌ No | ✅ Yes |
| Parallelization | ❌ Manual | ✅ Automatic |
| Fault tolerance | ❌ None | ✅ Checkpointing |
| State management | ❌ In-memory only | ✅ Managed by Flink |
| Monitoring | ❌ Manual | ✅ Flink UI |
| Scalability | ❌ Single process | ✅ Distributed |

## Adding Storage

### Write to HDFS

In `ResultPrinter.map()`:

```python
def map(self, value):
    data = json.loads(value)
    
    # Write to HDFS
    from hdfs3 import HDFileSystem
    hdfs = HDFileSystem(host='namenode', port=8020)
    
    date = data['timestamp'][:10]
    path = f"/smart-city/detections/{data['camera_id']}/{date}/"
    hdfs.mkdir(path, create_parents=True)
    
    filename = f"{path}/{data['timestamp']}.json"
    hdfs.write(filename, json.dumps(data).encode())
    
    return value
```

### Write to TimescaleDB

```python
def map(self, value):
    data = json.loads(value)
    
    # Write to TimescaleDB
    import psycopg2
    conn = psycopg2.connect(
        host='timescaledb',
        port=5432,
        database='realtime_analytics',
        user='smartcity',
        password='smartcity123'
    )
    
    cursor = conn.cursor()
    for det in data['detections']:
        cursor.execute("""
            INSERT INTO detections (...)
            VALUES (...)
        """)
    conn.commit()
    conn.close()
    
    return value
```

## Troubleshooting

### Job doesn't show in UI

Check logs:
```bash
docker exec flink-jobmanager cat /tmp/vision_job.log
```

Common issues:
- PyFlink not installed → Check Dockerfile
- Import errors → Rebuild containers
- Kafka not running → Start Kafka

### Task failures

Check TaskManager logs:
```bash
docker logs flink-taskmanager
```

Common issues:
- Out of memory → Increase TaskManager memory
- YOLO model not found → Check model download in Dockerfile

### Performance issues

Adjust parallelism:
```python
env.set_parallelism(4)  # Increase parallel tasks
```

## Summary

✅ **Proper PyFlink job** that uses Flink's engine  
✅ **Shows in Flink UI** for monitoring  
✅ **Distributed processing** across TaskManagers  
✅ **Fault tolerant** with checkpointing  
✅ **Managed state** per camera  
✅ **Production-ready** architecture  

This is the RIGHT way to use Flink for stream processing! 🚀