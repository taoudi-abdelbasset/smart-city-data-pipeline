#!/usr/bin/env python3
"""
RTSP to Kafka Bridge - Smart City Data Pipeline (AUTO-DISCOVERY)
Discovers cameras from MQTT registry
Dynamically connects to camera streams
Extracts video frames and publishes to Kafka topic
"""

import cv2
import json
import time
import sys
import os
import base64
import threading
from datetime import datetime
from kafka import KafkaProducer
import paho.mqtt.client as mqtt

class RTSPToKafkaBridge:
    """
    Bridge between RTSP camera streams and Kafka
    AUTO-DISCOVERS cameras from MQTT registry
    """
    
    def __init__(self):
        # MQTT Configuration (for camera discovery)
        self.mqtt_host = os.getenv("MQTT_HOST", "10.0.1.134")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        self.mqtt_client = None
        
        # Kafka Configuration
        self.kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.kafka_topic = "smart-city-camera-frames"
        self.kafka_producer = None
        
        # Camera registry
        self.camera_streams = {}
        self.camera_metadata = {}
        self.cameras_discovered = False
        
        # Frame capture settings
        self.frame_rate = int(os.getenv("FRAME_RATE", "2"))
        self.frame_resize = (int(os.getenv("FRAME_WIDTH", "640")), int(os.getenv("FRAME_HEIGHT", "480")))
        self.jpeg_quality = int(os.getenv("JPEG_QUALITY", "70"))
        
        # Threads
        self.capture_threads = []
        self.running = False
        
        # Statistics
        self.stats = {
            "frames_captured": 0,
            "frames_sent": 0,
            "errors": 0,
            "start_time": datetime.now(),
            "camera_stats": {}
        }
        
        print("🎥 RTSP to Kafka Bridge (AUTO-DISCOVERY)")
        print("=" * 80)
    
    def setup_mqtt(self):
        """Connect to MQTT to discover cameras"""
        print(f"\n📡 Connecting to MQTT: {self.mqtt_host}:{self.mqtt_port}")
        
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            print("✅ Connected to MQTT!")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to MQTT: {e}")
            return False
    
    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """Subscribe to camera registry"""
        print("🔔 Subscribing to camera registry...")
        client.subscribe("cameras/registry/list", qos=1)
        client.subscribe("cameras/+/info", qos=1)
        print("✅ Subscribed!")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Process camera registry messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            
            if topic == "cameras/registry/list":
                print(f"\n📋 Received camera list")
                self.process_camera_list(payload)
            elif topic.startswith("cameras/") and topic.endswith("/info"):
                camera_id = topic.split('/')[1]
                self.process_camera_info(camera_id, payload)
        except Exception as e:
            print(f"⚠️  MQTT error: {e}")
    
    def process_camera_list(self, data):
        """Build camera streams from registry"""
        cameras = data.get('cameras', [])
        print(f"   Found {len(cameras)} cameras")
        
        for camera in cameras:
            camera_id = camera.get('camera_id')
            rtsp_url = camera.get('rtsp', {}).get('url')
            
            if camera_id and rtsp_url:
                self.camera_streams[camera_id] = rtsp_url
                self.camera_metadata[camera_id] = camera
                self.stats["camera_stats"][camera_id] = {"captured": 0, "sent": 0, "errors": 0}
                print(f"   ✅ {camera_id}: {rtsp_url}")
        
        self.cameras_discovered = True
        print(f"\n🎯 Discovery complete: {len(self.camera_streams)} cameras")
    
    def process_camera_info(self, camera_id, data):
        """Update camera info"""
        rtsp_url = data.get('rtsp', {}).get('url')
        if rtsp_url and camera_id not in self.camera_streams:
            print(f"\n🆕 New camera: {camera_id}")
            self.camera_streams[camera_id] = rtsp_url
            self.camera_metadata[camera_id] = data
            self.stats["camera_stats"][camera_id] = {"captured": 0, "sent": 0, "errors": 0}
    
    def wait_for_cameras(self, timeout=30):
        """Wait for camera discovery"""
        print(f"\n⏳ Waiting for cameras (timeout: {timeout}s)...")
        start = time.time()
        while not self.cameras_discovered and (time.time() - start) < timeout:
            time.sleep(1)
        return self.cameras_discovered
    
    def setup_kafka(self):
        """Connect to Kafka"""
        print(f"\n📤 Connecting to Kafka: {self.kafka_bootstrap_servers}")
        
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                max_request_size=10485760,
                buffer_memory=33554432,
                compression_type='gzip',
                acks='all',
                retries=3
            )
            print("✅ Connected to Kafka!")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            return False
    
    def capture_camera_stream(self, camera_id, rtsp_url):
        """Capture frames from camera"""
        print(f"🎥 Starting: {camera_id}")
        cap = None
        
        while self.running:
            try:
                if cap is None or not cap.isOpened():
                    cap = cv2.VideoCapture(rtsp_url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if not cap.isOpened():
                        time.sleep(5)
                        continue
                    print(f"✅ Connected: {camera_id}")
                
                ret, frame = cap.read()
                if not ret:
                    cap.release()
                    cap = None
                    time.sleep(5)
                    continue
                
                self.stats["frames_captured"] += 1
                self.stats["camera_stats"][camera_id]["captured"] += 1
                self.process_and_send_frame(camera_id, frame)
                time.sleep(1.0 / self.frame_rate)
                
            except Exception as e:
                print(f"❌ Error {camera_id}: {e}")
                self.stats["errors"] += 1
                if cap:
                    cap.release()
                    cap = None
                time.sleep(5)
        
        if cap:
            cap.release()
    
    def process_and_send_frame(self, camera_id, frame):
        """Encode and send frame to Kafka"""
        try:
            frame = cv2.resize(frame, self.frame_resize)
            _, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            frame_b64 = base64.b64encode(encoded).decode('utf-8')
            
            metadata = self.camera_metadata.get(camera_id, {})
            
            message = {
                "camera_id": camera_id,
                "camera_name": metadata.get('camera_name', camera_id),
                "location": metadata.get('location', {}),
                "camera_type": metadata.get('camera_type', 'unknown'),
                "timestamp": datetime.now().isoformat(),
                "frame_timestamp": time.time(),
                "width": self.frame_resize[0],
                "height": self.frame_resize[1],
                "encoding": "jpeg",
                "compression_quality": self.jpeg_quality,
                "frame_data": frame_b64,
                "frame_size_bytes": len(frame_b64)
            }
            
            self.kafka_producer.send(self.kafka_topic, key=camera_id, value=message).get(timeout=5)
            
            self.stats["frames_sent"] += 1
            self.stats["camera_stats"][camera_id]["sent"] += 1
            
            if self.stats["frames_sent"] % 10 == 0:
                print(f"✅ [{self.stats['frames_sent']}] {camera_id} → Kafka ({len(frame_b64)/1024:.1f} KB)")
                
        except Exception as e:
            print(f"❌ Send error {camera_id}: {e}")
            self.stats["errors"] += 1
            self.stats["camera_stats"][camera_id]["errors"] += 1
    
    def print_stats(self):
        """Print statistics"""
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        print("\n" + "=" * 80)
        print("📊 Statistics")
        print("=" * 80)
        print(f"   Uptime: {uptime:.0f}s ({uptime/60:.1f}m)")
        print(f"   Cameras: {len(self.camera_streams)}")
        print(f"   Frames: {self.stats['frames_sent']}")
        print(f"   Errors: {self.stats['errors']}")
        print(f"   Rate: {self.stats['frames_sent']/(uptime or 1):.2f} fps")
        for cam, stats in self.stats["camera_stats"].items():
            print(f"      {cam}: {stats['sent']} sent, {stats['errors']} errors")
        print("=" * 80 + "\n")
    
    def run(self):
        """Main loop"""
        print("\n🚀 Starting Bridge...")
        print("=" * 80)
        print(f"   MQTT: {self.mqtt_host}:{self.mqtt_port}")
        print(f"   Kafka: {self.kafka_bootstrap_servers}")
        print(f"   Settings: {self.frame_rate}fps, {self.frame_resize}, {self.jpeg_quality}% quality")
        print("=" * 80 + "\n")
        
        if not self.setup_mqtt():
            sys.exit(1)
        
        if not self.wait_for_cameras():
            print("⚠️  No cameras found, waiting...")
        
        if not self.setup_kafka():
            sys.exit(1)
        
        self.running = True
        
        for camera_id, rtsp_url in self.camera_streams.items():
            thread = threading.Thread(target=self.capture_camera_stream, args=(camera_id, rtsp_url), daemon=True)
            thread.start()
            self.capture_threads.append(thread)
            time.sleep(1)
        
        try:
            while True:
                time.sleep(30)
                self.print_stats()
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
            self.running = False
            self.print_stats()
        finally:
            for thread in self.capture_threads:
                thread.join(timeout=5)
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            if self.kafka_producer:
                self.kafka_producer.flush()
                self.kafka_producer.close()
            print("✅ Stopped")


def main():
    bridge = RTSPToKafkaBridge()
    bridge.run()


if __name__ == "__main__":
    main()