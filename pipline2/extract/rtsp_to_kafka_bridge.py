#!/usr/bin/env python3
"""
Smart City - RTSP Camera to Kafka Bridge
Captures frames from RTSP streams and publishes to Kafka
Includes camera metadata from metadata.json files
"""

import json
import os
import sys
import cv2
import base64
import signal
import time
from datetime import datetime
from pathlib import Path
import multiprocessing

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    print("❌ kafka-python not installed. Install with: pip install kafka-python")
    KAFKA_AVAILABLE = False
    sys.exit(1)


class RTSPToKafkaBridge:
    """
    Captures frames from RTSP stream and publishes to Kafka
    Includes camera metadata (location, zone, etc.)
    """
    
    def __init__(self, 
                 camera_metadata_path,
                 rtsp_url,
                 kafka_bootstrap_servers="localhost:9092",
                 fps=1,  # Capture 1 frame per second
                 image_quality=85):
        
        self.metadata = self._load_metadata(camera_metadata_path)
        self.camera_id = self.metadata['camera_id']
        self.rtsp_url = rtsp_url
        self.kafka_bootstrap = kafka_bootstrap_servers
        self.fps = fps
        self.image_quality = image_quality
        
        self.kafka_producer = None
        self.video_capture = None
        
        self.frame_count = 0
        self.error_count = 0
        self.running = True
        
        print(f"\n{'='*80}")
        print(f"📹 Camera Bridge: {self.camera_id}")
        print(f"{'='*80}")
        print(f"RTSP URL: {rtsp_url}")
        print(f"Kafka: {kafka_bootstrap_servers}")
        print(f"Capture Rate: {fps} FPS")
        print(f"Image Quality: {image_quality}%")
        print(f"Location: {self.metadata['location']['address']}")
        print(f"Zone: {self.metadata['location']['zone']}")
        print(f"{'='*80}")
    
    def _load_metadata(self, metadata_path):
        """Load camera metadata from JSON file"""
        with open(metadata_path, 'r') as f:
            return json.load(f)
    
    def setup_kafka(self):
        """Initialize Kafka producer with optimized settings for images"""
        print(f"\n📡 Connecting to Kafka...")
        
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                
                # Optimized for large messages (images)
                max_request_size=10485760,  # 10 MB
                buffer_memory=33554432,      # 32 MB
                compression_type='gzip',
                
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            
            print(f"✅ Connected to Kafka!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            return False
    
    def setup_video_capture(self):
        """Initialize video capture from RTSP stream"""
        print(f"\n📹 Connecting to RTSP stream...")
        
        try:
            self.video_capture = cv2.VideoCapture(self.rtsp_url)
            
            # Set buffer size to 1 (latest frame)
            self.video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Check if stream opened
            if not self.video_capture.isOpened():
                raise Exception("Failed to open RTSP stream")
            
            # Test read
            ret, frame = self.video_capture.read()
            if not ret or frame is None:
                raise Exception("Failed to read frame from stream")
            
            print(f"✅ Connected to RTSP stream!")
            print(f"   Frame size: {frame.shape[1]}x{frame.shape[0]}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to RTSP: {e}")
            return False
    
    def capture_and_publish(self):
        """Main loop: capture frames and publish to Kafka"""
        
        frame_interval = 1.0 / self.fps
        last_capture_time = 0
        
        print(f"\n{'='*80}")
        print(f"🚀 Starting frame capture for {self.camera_id}")
        print(f"{'='*80}\n")
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check if it's time to capture
                if current_time - last_capture_time < frame_interval:
                    time.sleep(0.01)  # Small sleep to prevent CPU spinning
                    continue
                
                last_capture_time = current_time
                
                # Capture frame
                ret, frame = self.video_capture.read()
                
                if not ret or frame is None:
                    print(f"⚠️  Failed to read frame - reconnecting...")
                    self.error_count += 1
                    
                    # Try to reconnect
                    self.video_capture.release()
                    time.sleep(2)
                    
                    if not self.setup_video_capture():
                        print(f"❌ Cannot reconnect to stream")
                        break
                    
                    continue
                
                # Encode frame to JPEG
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.image_quality]
                ret, buffer = cv2.imencode('.jpg', frame, encode_param)
                
                if not ret:
                    print(f"⚠️  Failed to encode frame")
                    self.error_count += 1
                    continue
                
                # Convert to base64
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Create message payload
                payload = {
                    # Device metadata
                    "device_type": "rtsp_camera",
                    "camera_id": self.camera_id,
                    "camera_name": self.metadata['camera_name'],
                    "timestamp": datetime.now().isoformat(),
                    
                    # Location
                    "location": self.metadata['location'],
                    
                    # Frame data
                    "frame": {
                        "frame_number": self.frame_count,
                        "width": frame.shape[1],
                        "height": frame.shape[0],
                        "format": "jpeg",
                        "quality": self.image_quality,
                        "size_bytes": len(buffer),
                        "data": frame_base64  # Base64 encoded JPEG
                    },
                    
                    # Camera capabilities (from metadata)
                    "capabilities": self.metadata.get('capabilities', {}),
                    
                    # Monitoring info
                    "monitoring": self.metadata.get('monitoring', {}),
                    
                    # Bridge metadata
                    "_bridge_metadata": {
                        "rtsp_url": self.rtsp_url,
                        "kafka_topic": "camera-frames",
                        "bridge_timestamp": datetime.now().isoformat(),
                        "frame_id": self.frame_count
                    }
                }
                
                # Publish to Kafka
                future = self.kafka_producer.send(
                    topic='camera-frames',
                    value=payload,
                    key=self.camera_id
                )
                
                # Wait for confirmation
                record_metadata = future.get(timeout=10)
                
                self.frame_count += 1
                
                # Log every 10 frames
                if self.frame_count % 10 == 0:
                    print(f"📸 [{self.camera_id}] Captured {self.frame_count} frames "
                          f"(errors: {self.error_count}) - "
                          f"Last frame: {len(buffer)/1024:.1f} KB")
                
                # Detailed log (optional)
                if os.getenv('DEBUG', 'false').lower() == 'true':
                    print(f"\n✅ Frame #{self.frame_count}")
                    print(f"   Camera: {self.camera_id}")
                    print(f"   Size: {frame.shape[1]}x{frame.shape[0]}")
                    print(f"   JPEG: {len(buffer)/1024:.1f} KB")
                    print(f"   Kafka partition: {record_metadata.partition}, offset: {record_metadata.offset}")
                
            except KafkaError as e:
                print(f"\n❌ Kafka error: {e}")
                self.error_count += 1
                time.sleep(1)
                
            except KeyboardInterrupt:
                print(f"\n\n🛑 Stopping capture for {self.camera_id}...")
                self.running = False
                break
                
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                self.error_count += 1
                time.sleep(1)
    
    def run(self):
        """Start the bridge"""
        
        # Setup Kafka
        if not self.setup_kafka():
            print(f"\n❌ Cannot start without Kafka connection")
            return False
        
        # Setup video capture
        if not self.setup_video_capture():
            print(f"\n❌ Cannot start without RTSP connection")
            return False
        
        # Start capturing
        try:
            self.capture_and_publish()
        finally:
            self.cleanup()
        
        return True
    
    def cleanup(self):
        """Cleanup resources"""
        print(f"\n📊 Statistics for {self.camera_id}:")
        print(f"   Total frames captured: {self.frame_count}")
        print(f"   Total errors: {self.error_count}")
        if self.frame_count > 0:
            print(f"   Success rate: {(self.frame_count / (self.frame_count + self.error_count) * 100):.1f}%")
        
        if self.video_capture:
            self.video_capture.release()
            print(f"   ✅ Released video capture")
        
        if self.kafka_producer:
            self.kafka_producer.flush()
            self.kafka_producer.close()
            print(f"   ✅ Closed Kafka producer")


def run_camera_bridge(camera_folder, rtsp_url, kafka_servers, fps, quality):
    """
    Run bridge for single camera in separate process
    """
    metadata_path = camera_folder / "metadata.json"
    
    bridge = RTSPToKafkaBridge(
        camera_metadata_path=metadata_path,
        rtsp_url=rtsp_url,
        kafka_bootstrap_servers=kafka_servers,
        fps=fps,
        image_quality=quality
    )
    
    bridge.run()


def main():
    """
    Main function - starts bridges for all cameras
    """
    
    print("=" * 80)
    print("📹 RTSP to Kafka Bridge - Multi-Camera")
    print("=" * 80)
    
    # Configuration
    kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    rtsp_server = os.getenv('RTSP_SERVER', 'localhost')
    rtsp_port = int(os.getenv('RTSP_PORT', '8554'))
    fps = int(os.getenv('CAPTURE_FPS', '1'))
    quality = int(os.getenv('IMAGE_QUALITY', '85'))
    
    # Find camera folders
    cameras_dir = Path("cameras")
    
    if not cameras_dir.exists():
        print("❌ 'cameras/' folder not found")
        print("   Make sure you're running from camera-analytics directory")
        sys.exit(1)
    
    camera_folders = [f for f in cameras_dir.iterdir() if f.is_dir()]
    
    if not camera_folders:
        print("❌ No camera folders found")
        sys.exit(1)
    
    print(f"\n📹 Found {len(camera_folders)} cameras")
    print("=" * 80)
    
    # Build RTSP URLs for each camera
    camera_configs = []
    for i, folder in enumerate(sorted(camera_folders), 1):
        rtsp_url = f"rtsp://{rtsp_server}:{rtsp_port}/stream{i}"
        camera_configs.append((folder, rtsp_url))
        print(f"   {folder.name}: {rtsp_url}")
    
    print("\n" + "=" * 80)
    print("🚀 Starting camera bridges...")
    print(f"   Kafka: {kafka_servers}")
    print(f"   Capture Rate: {fps} FPS")
    print(f"   Image Quality: {quality}%")
    print("=" * 80 + "\n")
    
    # Start each camera in separate process
    processes = []
    
    try:
        for folder, rtsp_url in camera_configs:
            p = multiprocessing.Process(
                target=run_camera_bridge,
                args=(folder, rtsp_url, kafka_servers, fps, quality)
            )
            p.start()
            processes.append(p)
            print(f"✅ Started bridge for {folder.name}")
            time.sleep(1)  # Stagger starts
        
        print(f"\n🔥 All {len(processes)} camera bridges running!")
        print("   Press Ctrl+C to stop all\n")
        
        # Wait for all processes
        for p in processes:
            p.join()
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all camera bridges...")
        
        for p in processes:
            p.terminate()
        
        # Wait for graceful shutdown
        time.sleep(2)
        
        # Force kill if needed
        for p in processes:
            if p.is_alive():
                p.kill()
        
        for p in processes:
            p.join()
        
        print("✅ All camera bridges stopped")


if __name__ == "__main__":
    main()