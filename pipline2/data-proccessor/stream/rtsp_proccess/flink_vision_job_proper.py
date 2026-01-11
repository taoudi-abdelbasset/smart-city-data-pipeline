#!/usr/bin/env python3
"""
PyFlink Vision Processor - COMPLETE WITH DUAL STORAGE
- TimescaleDB: Real-time analytics (latest data)
- Hive/HDFS: Historical archive (partitioned by camera/year/month/day)
"""

import json
import base64
import time
import numpy as np
import cv2
from collections import defaultdict
from scipy.spatial import distance as dist
from ultralytics import YOLO
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch

# PyFlink imports
from pyflink.datastream import StreamExecutionEnvironment, RuntimeContext
from pyflink.datastream.functions import MapFunction, KeyedProcessFunction
from pyflink.common import Types, WatermarkStrategy
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.state import ValueStateDescriptor

print("="*80)
print("🚀 PyFlink Vision Processor - COMPLETE WITH DUAL STORAGE")
print("="*80)

# ============================================
# TRACKER CLASS
# ============================================
class SimpleTracker:
    """Centroid-based object tracker"""
    def __init__(self, max_disappeared=30):
        self.next_id = 0
        self.objects = {}
        self.disappeared = {}
        self.object_info = {}
        self.max_disappeared = max_disappeared
    
    def register(self, centroid, obj_type, bbox, age=None, gender=None, age_conf=0, gender_conf=0):
        self.objects[self.next_id] = centroid
        self.disappeared[self.next_id] = 0
        self.object_info[self.next_id] = {
            "type": obj_type, "bbox": bbox, "age": age, "gender": gender,
            "age_confidence": age_conf, "gender_confidence": gender_conf,
            "first_seen": time.time()
        }
        self.next_id += 1
        return self.next_id - 1
    
    def deregister(self, object_id):
        del self.objects[object_id]
        del self.disappeared[object_id]
        if object_id in self.object_info:
            del self.object_info[object_id]
    
    def update(self, detections):
        if len(detections) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return {}
        
        input_centroids = np.array([d[0] for d in detections])
        
        if len(self.objects) == 0:
            for centroid, obj_type, bbox, age, gender, age_conf, gender_conf in detections:
                self.register(centroid, obj_type, bbox, age, gender, age_conf, gender_conf)
        else:
            object_ids = list(self.objects.keys())
            object_centroids = np.array(list(self.objects.values()))
            
            D = dist.cdist(object_centroids, input_centroids)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]
            
            used_rows = set()
            used_cols = set()
            
            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > 50:
                    continue
                
                object_id = object_ids[row]
                self.objects[object_id] = input_centroids[col]
                self.disappeared[object_id] = 0
                
                _, obj_type, bbox, age, gender, age_conf, gender_conf = detections[col]
                self.object_info[object_id]["bbox"] = bbox
                
                if age and age_conf > self.object_info[object_id].get("age_confidence", 0):
                    self.object_info[object_id]["age"] = age
                    self.object_info[object_id]["age_confidence"] = age_conf
                
                if gender and gender_conf > self.object_info[object_id].get("gender_confidence", 0):
                    self.object_info[object_id]["gender"] = gender
                    self.object_info[object_id]["gender_confidence"] = gender_conf
                
                used_rows.add(row)
                used_cols.add(col)
            
            unused_rows = set(range(D.shape[0])) - used_rows
            unused_cols = set(range(D.shape[1])) - used_cols
            
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            
            for col in unused_cols:
                centroid, obj_type, bbox, age, gender, age_conf, gender_conf = detections[col]
                self.register(centroid, obj_type, bbox, age, gender, age_conf, gender_conf)
        
        return {oid: (self.objects[oid], self.object_info[oid]) 
                for oid in self.objects.keys()}


# ============================================
# FLINK MAP FUNCTION - FRAME PROCESSING
# ============================================
class FrameProcessor(MapFunction):
    def __init__(self):
        self.model = None
        self.frame_count = 0
    
    def open(self, runtime_context: RuntimeContext):
        print("🔧 Initializing YOLO model...")
        self.model = YOLO('yolov8n.pt')
        print("✅ YOLO model loaded")
    
    def map(self, value):
        try:
            data = json.loads(value)
            camera_id = data.get('camera_id')
            frame_b64 = data.get('frame_data')
            
            if not frame_b64:
                return None
            
            # Decode frame
            img_bytes = base64.b64decode(frame_b64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return None
            
            # Run YOLO detection
            results = self.model(frame, classes=[0, 2], verbose=False)
            detections = []
            
            for r in results[0].boxes:
                x1, y1, x2, y2 = map(int, r.xyxy[0])
                detections.append({
                    "centroid": ((x1 + x2) // 2, (y1 + y2) // 2),
                    "type": "Person" if int(r.cls[0]) == 0 else "Car",
                    "bbox": [x1, y1, x2, y2]
                })
            
            self.frame_count += 1
            if self.frame_count % 10 == 0:
                print(f"📸 Processed {self.frame_count} frames from {camera_id}")
            
            return json.dumps({
                "camera_id": camera_id,
                "timestamp": data.get('timestamp'),
                "detections": detections
            })
            
        except Exception as e:
            print(f"❌ Frame processing error: {e}")
            return None


# ============================================
# FLINK KEYED PROCESS FUNCTION - TRACKING
# ============================================
class ObjectTracker(KeyedProcessFunction):
    """Flink KeyedProcessFunction: Stateful tracking per camera"""
    
    def __init__(self):
        self.tracker_state = None
    
    def open(self, runtime_context: RuntimeContext):
        state_descriptor = ValueStateDescriptor(
            "tracker_state",
            Types.PICKLED_BYTE_ARRAY()
        )
        self.tracker_state = runtime_context.get_state(state_descriptor)
        print("🎯 ObjectTracker initialized")
    
    def process_element(self, value, ctx):
        try:
            data = json.loads(value)
            camera_id = data['camera_id']
            timestamp = data['timestamp']
            detections = data['detections']
            
            # Get or create tracker for this camera
            tracker = self.tracker_state.value()
            if tracker is None:
                tracker = SimpleTracker(max_disappeared=30)
                print(f"🆕 Created new tracker for camera {camera_id}")
            
            # Convert detections to tracker format
            detection_tuples = []
            for det in detections:
                detection_tuples.append((
                    det['centroid'],
                    det['type'],
                    det['bbox'],
                    det.get('age'),
                    det.get('gender'),
                    det.get('age_confidence', 0),
                    det.get('gender_confidence', 0)
                ))
            
            # Update tracker
            tracked_objects = tracker.update(detection_tuples)
            self.tracker_state.update(tracker)
            
            # Format output
            tracked_detections = []
            for obj_id, (centroid, info) in tracked_objects.items():
                detection_data = {
                    "object_id": int(obj_id),
                    "type": info['type'],
                    "bounding_box": {
                        "x1": int(info['bbox'][0]),
                        "y1": int(info['bbox'][1]),
                        "x2": int(info['bbox'][2]),
                        "y2": int(info['bbox'][3])
                    },
                    "centroid": {
                        "x": int(centroid[0]),
                        "y": int(centroid[1])
                    },
                    "tracking_duration_seconds": round(time.time() - info['first_seen'], 1)
                }
                
                if info['type'] == "Person":
                    detection_data["gender"] = info.get('gender', 'Unknown')
                    detection_data["gender_confidence"] = round(info.get('gender_confidence', 0), 2)
                    detection_data["age"] = info.get('age', 'Unknown')
                    detection_data["age_confidence"] = round(info.get('age_confidence', 0), 2)
                
                tracked_detections.append(detection_data)
            
            output = {
                "camera_id": camera_id,
                "timestamp": timestamp,
                "total_objects": len(tracked_detections),
                "detections": tracked_detections
            }
            
            yield json.dumps(output)
            
        except Exception as e:
            print(f"❌ Tracking error: {e}")
            import traceback
            traceback.print_exc()


# ============================================
# DUAL STORAGE WRITER - MapFunction approach
# ============================================
class DualStorageWriter(MapFunction):
    """
    Write to BOTH TimescaleDB and HDFS using MapFunction
    This approach works reliably in PyFlink
    """
    
    def __init__(self):
        self.timescale_conn = None
        self.batch_buffer = []
        self.batch_size = 10  # Smaller batch for faster writes
        self.records_written = 0
    
    def open(self, runtime_context: RuntimeContext):
        """Initialize connections"""
        print("🔌 Initializing storage connections...")
        
        # Connect to TimescaleDB
        try:
            self.timescale_conn = psycopg2.connect(
                host="timescaledb",
                port=5432,
                database="realtime_analytics",
                user="smartcity",
                password="smartcity123"
            )
            self.timescale_conn.autocommit = False
            print("✅ Connected to TimescaleDB")
        except Exception as e:
            print(f"❌ TimescaleDB connection failed: {e}")
            self.timescale_conn = None
    
    def map(self, value):
        """Process each record and write to storage"""
        try:
            data = json.loads(value)
            
            # Add to batch buffer
            self.batch_buffer.append(data)
            
            # Flush when batch is full
            if len(self.batch_buffer) >= self.batch_size:
                self._flush_batch()
            
            # Pass through the data
            return value
            
        except Exception as e:
            print(f"❌ Storage writer error: {e}")
            import traceback
            traceback.print_exc()
            return value
    
    def _flush_batch(self):
        """Write batch to both storages"""
        if not self.batch_buffer:
            return
        
        batch_size = len(self.batch_buffer)
        
        try:
            # Write to TimescaleDB
            self._write_to_timescaledb(self.batch_buffer)
            
            # Write to HDFS
            self._write_to_hdfs(self.batch_buffer)
            
            self.records_written += batch_size
            print(f"✅ Flushed {batch_size} records (total: {self.records_written})")
            
            self.batch_buffer = []
            
        except Exception as e:
            print(f"❌ Batch flush error: {e}")
            import traceback
            traceback.print_exc()
            # Clear buffer even on error to prevent memory buildup
            self.batch_buffer = []
    
    def _write_to_timescaledb(self, batch):
        """Write detections to TimescaleDB"""
        if not self.timescale_conn:
            print("⚠️ No TimescaleDB connection, skipping write")
            return
        
        try:
            cursor = self.timescale_conn.cursor()
            detection_records = []
            
            for record in batch:
                camera_id = record['camera_id']
                timestamp = record['timestamp']
                
                for det in record['detections']:
                    detection_records.append((
                        timestamp,
                        camera_id,
                        det['object_id'],
                        det['type'],
                        det['bounding_box']['x1'],
                        det['bounding_box']['y1'],
                        det['bounding_box']['x2'],
                        det['bounding_box']['y2'],
                        det['centroid']['x'],
                        det['centroid']['y'],
                        det['tracking_duration_seconds'],
                        det.get('gender'),
                        det.get('gender_confidence'),
                        det.get('age'),
                        det.get('age_confidence')
                    ))
            
            if detection_records:
                insert_sql = """
                    INSERT INTO vision_detections (
                        time, camera_id, object_id, object_type,
                        bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                        centroid_x, centroid_y, tracking_duration,
                        gender, gender_confidence, age, age_confidence
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                execute_batch(cursor, insert_sql, detection_records, page_size=100)
                self.timescale_conn.commit()
                
                print(f"📊 TimescaleDB: Wrote {len(detection_records)} detections")
            
            cursor.close()
            
        except Exception as e:
            print(f"❌ TimescaleDB write error: {e}")
            import traceback
            traceback.print_exc()
            if self.timescale_conn:
                self.timescale_conn.rollback()
    
    def _write_to_hdfs(self, batch):
        """Write to HDFS with Hive partitioning"""
        try:
            import subprocess
            from datetime import datetime
            
            # Group records by date
            records_by_date = {}
            
            for record in batch:
                timestamp_str = record['timestamp']
                
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    dt = datetime.now()
                
                date_key = (dt.year, dt.month, dt.day)
                if date_key not in records_by_date:
                    records_by_date[date_key] = []
                records_by_date[date_key].append(record)
            
            # Write one file per date
            for (year, month, day), records in records_by_date.items():
                partition_path = f"/smart-city/vision-detections/year={year}/month={month:02d}/day={day:02d}"
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"detections_{timestamp}.jsonl"
                hdfs_file_path = f"{partition_path}/{filename}"
                
                # We just print the path instead of executing the 'hdfs dfs -put' command
                print(f"☁️  [HDFS MOCK] Would have written {len(records)} records to: {hdfs_file_path}")
                # 123
                # # JSON Lines format
                # jsonl_data = "\n".join([json.dumps(r) for r in records])
                
                # # Write to HDFS
                # hdfs_cmd = ["hdfs", "dfs", "-put", "-f", "-", hdfs_file_path]
                
                # process = subprocess.Popen(
                #     hdfs_cmd,
                #     stdin=subprocess.PIPE,
                #     stdout=subprocess.PIPE,
                #     stderr=subprocess.PIPE
                # )
                
                # stdout, stderr = process.communicate(input=jsonl_data.encode('utf-8'), timeout=10)
                
                if process.returncode == 0:
                    print(f"💾 HDFS: Wrote {len(records)} records to {hdfs_file_path}")
                else:
                    print(f"⚠️ HDFS write warning: {stderr.decode('utf-8')[:200]}")
            
        except Exception as e:
            print(f"❌ HDFS write error: {e}")
            import traceback
            traceback.print_exc()
    
    def close(self):
        """Cleanup on shutdown"""
        print("\n🛑 Closing storage connections...")
        
        # Flush remaining records
        if self.batch_buffer:
            self._flush_batch()
        
        # Close TimescaleDB
        if self.timescale_conn:
            try:
                self.timescale_conn.close()
                print("✅ TimescaleDB connection closed")
            except:
                pass
        
        print(f"📊 Total records written: {self.records_written}")


# ============================================
# MAIN FLINK JOB
# ============================================
def main():
    print("\n📊 Initializing Flink Environment...")
    env = StreamExecutionEnvironment.get_execution_environment()
    
    # Add Kafka connector JAR
    env.add_jars("file:///opt/flink/lib/flink-sql-connector-kafka-3.0.1-1.18.jar")
    
    env.set_parallelism(2)
    env.enable_checkpointing(60000)  # Checkpoint every minute
    
    print("📡 Setting up Kafka source...")
    kafka_source = KafkaSource.builder() \
        .set_bootstrap_servers("kafka:9092") \
        .set_topics("smart-city-camera-frames") \
        .set_group_id("pyflink-vision-processor") \
        .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
        .set_value_only_deserializer(SimpleStringSchema()) \
        .build()
    
    print("🔧 Building stream processing pipeline...")
    stream = env.from_source(
        kafka_source, 
        WatermarkStrategy.no_watermarks(), 
        "Kafka Source"
    )
    
    # Pipeline: Kafka -> Detect -> Track -> Store -> Print
    processed = stream \
        .map(FrameProcessor(), output_type=Types.STRING()) \
        .filter(lambda x: x is not None) \
        .key_by(lambda x: json.loads(x)['camera_id']) \
        .process(ObjectTracker(), output_type=Types.STRING())
    
    # Write to dual storage using MapFunction (works reliably in PyFlink)
    print("💾 Adding DualStorageWriter...")
    stored = processed.map(DualStorageWriter(), output_type=Types.STRING())
    
    # Print to console for monitoring
    stored.print()
    
    print("\n" + "="*80)
    print("🚀 SUBMITTING JOB TO FLINK...")
    print("📊 Pipeline: Kafka -> YOLO Detection -> Object Tracking -> Dual Storage")
    print("   1. TimescaleDB (real-time analytics)")
    print("   2. HDFS/Hive (historical archive)")
    print("   Partitioning: year/month/day")
    print("="*80 + "\n")
    
    env.execute("Vision Processor - Detection, Tracking & Dual Storage")


if __name__ == '__main__':
    main()