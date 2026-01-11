#!/usr/bin/env python3
"""
Smart City - MQTT to Kafka Bridge
Subscribes to all MQTT topics from IoT sensors and publishes to Kafka topics
Handles: Air Quality, Parking, SUMO Traffic data
"""

import json
import os
import sys
import signal
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    print("❌ paho-mqtt not installed. Install with: pip install paho-mqtt")
    MQTT_AVAILABLE = False
    sys.exit(1)

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    print("❌ kafka-python not installed. Install with: pip install kafka-python")
    KAFKA_AVAILABLE = False
    sys.exit(1)


class MQTTToKafkaBridge:
    """
    Bridge between MQTT and Kafka
    - Subscribes to MQTT topics: air_quality/#, parking/#, traffic/#
    - Publishes to Kafka topics with same structure
    """
    
    def __init__(self, 
                 mqtt_host="localhost", 
                 mqtt_port=1883,
                 kafka_bootstrap_servers="localhost:9092"):
        
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.kafka_bootstrap = kafka_bootstrap_servers
        
        self.mqtt_client = None
        self.kafka_producer = None
        
        self.message_count = 0
        self.error_count = 0
        
        print("=" * 80)
        print("🌉 MQTT to Kafka Bridge")
        print("=" * 80)
        print(f"MQTT Broker: {mqtt_host}:{mqtt_port}")
        print(f"Kafka Broker: {kafka_bootstrap_servers}")
        print("=" * 80)
    
    def setup_kafka(self):
        """Initialize Kafka producer"""
        print("\n📡 Connecting to Kafka...")
        
        try:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
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
        """Initialize MQTT client and callbacks"""
        print("\n📡 Connecting to MQTT...")
        
        try:
            self.mqtt_client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id="mqtt_kafka_bridge"
            )
            
            # Set callbacks
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            
            # Connect
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            
            print("✅ Connected to MQTT!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to MQTT: {e}")
            return False
    
    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """Callback when connected to MQTT broker"""
        print("\n🔌 MQTT Connected! Subscribing to topics...")
        
        # Subscribe to all IoT sensor topics
        topics = [
            ("air_quality/#", 0),      # Air quality sensors
            ("parking/#", 0),          # Parking sensors
            ("traffic/#", 0),          # SUMO traffic data
        ]
        
        for topic, qos in topics:
            client.subscribe(topic, qos)
            print(f"   ✅ Subscribed to: {topic}")
        
        print("\n" + "=" * 80)
        print("🚀 Bridge is LIVE - forwarding MQTT → Kafka")
        print("=" * 80 + "\n")
    
    def on_mqtt_disconnect(self, client, userdata, flags, reason_code, properties):
        """Callback when disconnected from MQTT"""
        print(f"\n⚠️  Disconnected from MQTT (reason: {reason_code})")
        print("   Attempting to reconnect...")
    
    def on_mqtt_message(self, client, userdata, msg):
        """
        Callback when message received from MQTT
        Forwards to appropriate Kafka topic
        """
        try:
            # Parse MQTT topic
            mqtt_topic = msg.topic
            
            # Parse payload
            try:
                payload = json.loads(msg.payload.decode('utf-8'))
            except json.JSONDecodeError:
                print(f"⚠️  Invalid JSON from {mqtt_topic}")
                self.error_count += 1
                return
            
            # Determine Kafka topic based on MQTT topic structure
            kafka_topic = self.map_mqtt_to_kafka_topic(mqtt_topic, payload)
            
            # Add bridge metadata
            payload['_bridge_metadata'] = {
                'mqtt_topic': mqtt_topic,
                'kafka_topic': kafka_topic,
                'bridge_timestamp': datetime.now().isoformat(),
                'message_id': self.message_count
            }
            
            # Generate message key (for partitioning)
            message_key = self.generate_message_key(mqtt_topic, payload)
            
            # Publish to Kafka
            future = self.kafka_producer.send(
                topic=kafka_topic,
                value=payload,
                key=message_key
            )
            
            # Wait for confirmation (with timeout)
            record_metadata = future.get(timeout=10)
            
            self.message_count += 1
            
            # Log every 10 messages
            if self.message_count % 10 == 0:
                print(f"📊 Forwarded {self.message_count} messages (errors: {self.error_count})")
            
            # Detailed log for debugging (optional)
            if os.getenv('DEBUG', 'false').lower() == 'true':
                print(f"\n✅ Message #{self.message_count}")
                print(f"   MQTT:  {mqtt_topic}")
                print(f"   Kafka: {kafka_topic} (partition {record_metadata.partition}, offset {record_metadata.offset})")
                print(f"   Key:   {message_key}")
                print(f"   Size:  {len(msg.payload)} bytes")
            
        except KafkaError as e:
            print(f"\n❌ Kafka error: {e}")
            print(f"   Topic: {mqtt_topic}")
            self.error_count += 1
            
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print(f"   Topic: {mqtt_topic}")
            self.error_count += 1
    
    def map_mqtt_to_kafka_topic(self, mqtt_topic, payload):
        """
        Map MQTT topic structure to Kafka topic
        
        MQTT Topics:
        - air_quality/{sensor_id}/data
        - parking/{lot_id}/event
        - parking/{lot_id}/status
        - traffic/sumo/edges/{edge_id}
        - traffic/sumo/vehicles/{vehicle_id}
        - traffic/sumo/traffic_lights/{tl_id}
        - traffic/sumo/simulation/stats
        
        Kafka Topics:
        - air-quality-data
        - parking-events
        - parking-status
        - traffic-edges
        - traffic-vehicles
        - traffic-lights
        - traffic-stats
        """
        
        parts = mqtt_topic.split('/')
        
        # Air quality: air_quality/{sensor_id}/data
        if parts[0] == 'air_quality':
            return 'air-quality-data'
        
        # Parking: parking/{lot_id}/{event|status}
        elif parts[0] == 'parking':
            if len(parts) >= 3:
                event_type = parts[2]
                if event_type == 'event':
                    return 'parking-events'
                elif event_type == 'status':
                    return 'parking-status'
        
        # Traffic: traffic/sumo/{category}/...
        elif parts[0] == 'traffic' and parts[1] == 'sumo':
            if len(parts) >= 3:
                category = parts[2]
                if category == 'edges':
                    return 'traffic-edges'
                elif category == 'vehicles':
                    return 'traffic-vehicles'
                elif category == 'traffic_lights':
                    return 'traffic-lights'
                elif category == 'simulation':
                    return 'traffic-stats'
        
        # Default fallback
        return 'iot-data-raw'
    
    def generate_message_key(self, mqtt_topic, payload):
        """
        Generate message key for Kafka partitioning
        Ensures messages from same sensor/device go to same partition
        """
        
        # Extract sensor/device ID from payload
        sensor_id = (
            payload.get('sensor_id') or 
            payload.get('parking_lot_id') or 
            payload.get('vehicle_id') or 
            payload.get('edge_id') or 
            payload.get('traffic_light_id') or
            mqtt_topic.split('/')[1] if len(mqtt_topic.split('/')) > 1 else 'unknown'
        )
        
        return str(sensor_id)
    
    def run(self):
        """Main loop - start forwarding messages"""
        
        # Setup connections
        if not self.setup_kafka():
            print("\n❌ Cannot start without Kafka connection")
            sys.exit(1)
        
        if not self.setup_mqtt():
            print("\n❌ Cannot start without MQTT connection")
            sys.exit(1)
        
        # Start MQTT loop
        try:
            print("\n" + "=" * 80)
            print("▶️  Bridge running - Press Ctrl+C to stop")
            print("=" * 80 + "\n")
            
            self.mqtt_client.loop_forever()
            
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down bridge...")
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup connections"""
        print("\n📊 Final Statistics:")
        print(f"   Total messages forwarded: {self.message_count}")
        print(f"   Total errors: {self.error_count}")
        print(f"   Success rate: {(self.message_count / (self.message_count + self.error_count) * 100):.1f}%")
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("   ✅ Disconnected from MQTT")
        
        if self.kafka_producer:
            self.kafka_producer.flush()
            self.kafka_producer.close()
            print("   ✅ Disconnected from Kafka")
        
        print("\n✅ Bridge stopped cleanly")


def main():
    """Main function"""
    
    # Configuration from environment variables
    mqtt_host = os.getenv('MQTT_HOST', 'localhost')
    mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
    kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    
    # Create and run bridge
    bridge = MQTTToKafkaBridge(
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        kafka_bootstrap_servers=kafka_servers
    )
    
    # Handle signals
    def signal_handler(sig, frame):
        print("\n\n🛑 Received interrupt signal...")
        bridge.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run
    bridge.run()


if __name__ == "__main__":
    main()