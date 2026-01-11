#!/usr/bin/env python3
"""
MQTT to Kafka Bridge - Smart City Data Pipeline
Connects to MQTT broker on simulation VM (10.0.1.134)
Extracts IoT sensor data and publishes to Kafka topics
"""

import json
import time
import signal
import sys
from datetime import datetime
from kafka import KafkaProducer
import paho.mqtt.client as mqtt

class MQTTToKafkaBridge:
    """
    Bridge between MQTT (simulation VM) and Kafka (pipeline VM)
    Subscribes to all MQTT topics and forwards to appropriate Kafka topics
    """
    
    def __init__(self):
        # MQTT Configuration (Simulation VM)
        self.mqtt_host = "10.0.1.134"
        self.mqtt_port = 1883
        self.mqtt_client = None
        
        # Kafka Configuration (Local - Pipeline VM)
        self.kafka_bootstrap_servers = "localhost:9093"
        self.kafka_producer = None
        
        # Statistics
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
            "start_time": datetime.now()
        }
        
        # Topic mapping: MQTT topic pattern -> Kafka topic
        self.topic_mapping = {
            "air_quality": "smart-city-air-quality",
            "parking": "smart-city-parking",
            "traffic/sumo/edges": "smart-city-traffic-edges",
            "traffic/sumo/vehicles": "smart-city-traffic-vehicles",
            "traffic/sumo/traffic_lights": "smart-city-traffic-lights",
            "traffic/sumo/simulation": "smart-city-simulation-stats"
        }
        
        print("🌉 MQTT to Kafka Bridge Initializing...")
        print("=" * 80)
    
    def setup_kafka(self):
        """Initialize Kafka producer"""
        print(f"\n📤 Connecting to Kafka: {self.kafka_bootstrap_servers}")
        
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1,
                compression_type='gzip'
            )
            print("✅ Connected to Kafka!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            return False
    
    def setup_mqtt(self):
        """Initialize MQTT client and connect to simulation VM"""
        print(f"\n📥 Connecting to MQTT Broker: {self.mqtt_host}:{self.mqtt_port}")
        
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            
            # Set callbacks
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            
            # Connect
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            print("✅ Connected to MQTT Broker!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to MQTT: {e}")
            return False
    
    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """Callback when connected to MQTT broker"""
        print("\n🔔 MQTT Connected! Subscribing to all topics...")
        
        # Subscribe to ALL topics with wildcard
        client.subscribe("#", qos=1)
        
        print("✅ Subscribed to all MQTT topics (#)")
        print("\n📊 Waiting for messages...")
        print("=" * 80)
    
    def on_mqtt_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """Callback when disconnected from MQTT broker"""
        print(f"\n⚠️  MQTT Disconnected (reason: {reason_code})")
        print("   Attempting reconnection...")
    
    def get_kafka_topic(self, mqtt_topic):
        """
        Map MQTT topic to Kafka topic
        
        Examples:
        - air_quality/SENSOR_001/data -> smart-city-air-quality
        - parking/LOT_DOWNTOWN_001/status -> smart-city-parking
        - traffic/sumo/edges/edge123 -> smart-city-traffic-edges
        """
        for pattern, kafka_topic in self.topic_mapping.items():
            if mqtt_topic.startswith(pattern):
                return kafka_topic
        
        # Default topic for unmapped messages
        return "smart-city-raw-data"
    
    def get_message_key(self, mqtt_topic, payload):
        """
        Extract key from message for Kafka partitioning
        Ensures messages from same device go to same partition
        """
        try:
            # Parse payload
            data = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
            
            # Extract device/sensor ID
            if "sensor_id" in data:
                return data["sensor_id"]
            elif "parking_lot_id" in data:
                return data["parking_lot_id"]
            elif "vehicle_id" in data:
                return data["vehicle_id"]
            elif "edge_id" in data:
                return data["edge_id"]
            elif "traffic_light_id" in data:
                return data["traffic_light_id"]
            else:
                # Use MQTT topic as key
                return mqtt_topic.split('/')[-1]
        
        except:
            return mqtt_topic
    
    def on_mqtt_message(self, client, userdata, msg):
        """Callback when MQTT message received"""
        try:
            mqtt_topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Skip system topics
            if mqtt_topic.startswith('$SYS/'):
                return
            
            self.stats["messages_received"] += 1
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                print(f"⚠️  Invalid JSON from {mqtt_topic}")
                self.stats["errors"] += 1
                return
            
            # Add metadata
            enriched_data = {
                "mqtt_topic": mqtt_topic,
                "timestamp": datetime.now().isoformat(),
                "bridge_received_at": datetime.now().isoformat(),
                "data": data
            }
            
            # Determine Kafka topic
            kafka_topic = self.get_kafka_topic(mqtt_topic)
            
            # Get message key for partitioning
            message_key = self.get_message_key(mqtt_topic, data)
            
            # Send to Kafka
            future = self.kafka_producer.send(
                kafka_topic,
                key=message_key,
                value=enriched_data
            )
            
            # Wait for send confirmation (with timeout)
            future.get(timeout=10)
            
            self.stats["messages_sent"] += 1
            
            # Log every 10th message
            if self.stats["messages_sent"] % 10 == 0:
                print(f"✅ [{self.stats['messages_sent']}] {mqtt_topic} → {kafka_topic} (key: {message_key})")
            
        except Exception as e:
            print(f"❌ Error processing message from {msg.topic}: {e}")
            self.stats["errors"] += 1
    
    def print_stats(self):
        """Print current statistics"""
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        
        print("\n" + "=" * 80)
        print("📊 Bridge Statistics")
        print("=" * 80)
        print(f"   Uptime: {uptime:.0f} seconds ({uptime/60:.1f} minutes)")
        print(f"   Messages received (MQTT): {self.stats['messages_received']}")
        print(f"   Messages sent (Kafka): {self.stats['messages_sent']}")
        print(f"   Errors: {self.stats['errors']}")
        print(f"   Throughput: {self.stats['messages_sent']/(uptime or 1):.2f} msg/s")
        print("=" * 80 + "\n")
    
    def run(self):
        """Main loop"""
        print("\n🚀 Starting MQTT to Kafka Bridge...")
        print("=" * 80)
        print("   Source: MQTT Broker (10.0.1.134:1883)")
        print("   Destination: Kafka (localhost:9093)")
        print("   Press Ctrl+C to stop")
        print("=" * 80 + "\n")
        
        # Setup connections
        if not self.setup_kafka():
            sys.exit(1)
        
        if not self.setup_mqtt():
            sys.exit(1)
        
        # Start MQTT loop
        self.mqtt_client.loop_start()
        
        # Monitor and print stats periodically
        try:
            while True:
                time.sleep(30)  # Print stats every 30 seconds
                self.print_stats()
        
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping bridge...")
            self.print_stats()
        
        finally:
            # Cleanup
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            if self.kafka_producer:
                self.kafka_producer.flush()
                self.kafka_producer.close()
            
            print("✅ Bridge stopped gracefully")


def main():
    """Entry point"""
    bridge = MQTTToKafkaBridge()
    bridge.run()


if __name__ == "__main__":
    main()