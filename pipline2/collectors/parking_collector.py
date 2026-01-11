#!/usr/bin/env python3
"""
Parking Data Collector - Kafka to HDFS
Collects parking lot data from Kafka and writes to HDFS in batches
Partitioned by: year/month/day/hour
"""

import json
import time
import os
import subprocess
from datetime import datetime
from kafka import KafkaConsumer
from collections import defaultdict

class ParkingCollector:
    """
    Batch collector for parking data
    Reads from Kafka, buffers events, writes to HDFS
    """
    
    def __init__(self):
        # Kafka settings - READ FROM ENVIRONMENT!
        self.kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.kafka_topic = os.getenv("KAFKA_TOPIC", "smart-city-parking")
        self.consumer_group = os.getenv("CONSUMER_GROUP", "parking-hdfs-collector")
        
        # Batch settings - READ FROM ENVIRONMENT!
        self.batch_size = int(os.getenv("BATCH_SIZE", "50"))
        self.batch_time = int(os.getenv("BATCH_TIME", "60"))
        
        # HDFS path
        self.hdfs_base_path = os.getenv("HDFS_BASE_PATH", "/smart-city/parking")
        
        # Buffers
        self.batch_buffer = []
        self.last_flush_time = time.time()
        
        # Statistics
        self.stats = {
            "records_consumed": 0,
            "batches_written": 0,
            "records_written": 0,
            "errors": 0,
            "start_time": datetime.now()
        }
        
        print("=" * 80)
        print("🅿️  Parking Collector - Kafka → HDFS")
        print("=" * 80)
        print(f"Kafka Bootstrap: {self.kafka_bootstrap}")
        print(f"Kafka Topic: {self.kafka_topic}")
        print(f"Consumer Group: {self.consumer_group}")
        print(f"Batch Size: {self.batch_size} records")
        print(f"Batch Time: {self.batch_time} seconds")
        print(f"HDFS Path: {self.hdfs_base_path}")
        print("=" * 80 + "\n")
    
    def connect_kafka(self):
        """Connect to Kafka consumer"""
        print(f"📡 Connecting to Kafka ({self.kafka_bootstrap})...")
        
        try:
            self.consumer = KafkaConsumer(
                self.kafka_topic,
                bootstrap_servers=self.kafka_bootstrap,
                group_id=self.consumer_group,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
                # NO TIMEOUTS - wait forever for events!
            )
            print("✅ Connected to Kafka!\n")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def should_flush(self):
        """Check if we should flush the batch"""
        size_trigger = len(self.batch_buffer) >= self.batch_size
        time_trigger = (time.time() - self.last_flush_time) >= self.batch_time
        return size_trigger or time_trigger
    
    def write_to_hdfs(self, records):
        """Write batch to HDFS with time-based partitioning"""
        if not records:
            return
        
        try:
            # Group by timestamp for partitioning
            records_by_time = defaultdict(list)
            
            for record in records:
                # Extract timestamp from nested data structure
                timestamp = None
                if 'data' in record and isinstance(record['data'], dict):
                    timestamp = record['data'].get('timestamp')
                if not timestamp:
                    timestamp = record.get('timestamp', datetime.now().isoformat())
                
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    dt = datetime.now()
                
                # Partition key: year/month/day/hour
                partition_key = (dt.year, dt.month, dt.day, dt.hour)
                records_by_time[partition_key].append(record)
            
            # Write one file per partition
            for (year, month, day, hour), partition_records in records_by_time.items():
                # Build HDFS path
                hdfs_path = f"{self.hdfs_base_path}/year={year}/month={month:02d}/day={day:02d}/hour={hour:02d}"
                
                # Generate filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = f"parking_{timestamp}.jsonl"
                full_path = f"{hdfs_path}/{filename}"
                
                # Convert to JSON Lines
                jsonl_data = "\n".join([json.dumps(r) for r in partition_records])
                
                # Write to HDFS
                hdfs_cmd = ["hdfs", "dfs", "-put", "-f", "-", full_path]
                
                process = subprocess.Popen(
                    hdfs_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = process.communicate(
                    input=jsonl_data.encode('utf-8'),
                    timeout=30
                )
                
                if process.returncode == 0:
                    print(f"💾 Wrote {len(partition_records)} records to {full_path}")
                    self.stats["batches_written"] += 1
                    self.stats["records_written"] += len(partition_records)
                else:
                    print(f"⚠️  HDFS write warning: {stderr.decode('utf-8')[:200]}")
                    self.stats["errors"] += 1
            
        except Exception as e:
            print(f"❌ HDFS write error: {e}")
            self.stats["errors"] += 1
            import traceback
            traceback.print_exc()
    
    def flush_batch(self):
        """Flush current batch to HDFS"""
        if not self.batch_buffer:
            return
        
        print(f"\n📤 Flushing batch ({len(self.batch_buffer)} records)...")
        self.write_to_hdfs(self.batch_buffer)
        
        self.batch_buffer = []
        self.last_flush_time = time.time()
    
    def print_stats(self):
        """Print statistics"""
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        
        print("\n" + "=" * 80)
        print("📊 Parking Collector Statistics")
        print("=" * 80)
        print(f"Uptime: {uptime:.0f}s ({uptime/60:.1f}m)")
        print(f"Records consumed: {self.stats['records_consumed']}")
        print(f"Records written: {self.stats['records_written']}")
        print(f"Batches written: {self.stats['batches_written']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Rate: {self.stats['records_consumed']/(uptime or 1):.2f} records/s")
        print(f"Buffer: {len(self.batch_buffer)} records")
        print("=" * 80 + "\n")
    
    def run(self):
        """Main loop"""
        print("🚀 Starting Parking Collector...")
        print("   Press Ctrl+C to stop\n")
        
        if not self.connect_kafka():
            return
        
        try:
            for message in self.consumer:
                # Extract data
                data = message.value
                
                # Add to batch
                self.batch_buffer.append(data)
                self.stats["records_consumed"] += 1
                
                # Log every 10 records
                if self.stats["records_consumed"] % 10 == 0:
                    mqtt_topic = data.get('mqtt_topic', 'unknown')
                    print(f"📥 [{self.stats['records_consumed']}] Received from {mqtt_topic}")
                
                # Flush if needed
                if self.should_flush():
                    self.flush_batch()
                
                # Print stats every 100 records
                if self.stats["records_consumed"] % 100 == 0:
                    self.print_stats()
        
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping collector...")
            self.flush_batch()
            self.print_stats()
        
        finally:
            if hasattr(self, 'consumer'):
                self.consumer.close()
            print("✅ Collector stopped")


if __name__ == "__main__":
    collector = ParkingCollector()
    collector.run()
