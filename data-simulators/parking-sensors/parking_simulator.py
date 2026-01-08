#!/usr/bin/env python3
"""
Smart City - Parking Lot IoT Simulator
Simulates parking sensors (magnetic loops, ultrasonic sensors)
Sends REAL data via MQTT protocol (simulates LoRaWAN gateway output)
"""

import json
import time
import random
from datetime import datetime
from pathlib import Path

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("⚠️  paho-mqtt not installed. Install with: pip install paho-mqtt")

class ParkingLotIoT:
    """
    Simulates parking lot with IoT sensors
    Each parking spot has a sensor (magnetic or ultrasonic)
    Sends data on state changes + periodic updates
    """
    
    def __init__(self, config_file, mqtt_client=None):
        self.config = self._load_config(config_file)
        self.parking_lot_id = self.config['parking_lot_id']
        self.total_spots = self.config['total_spots']
        self.mqtt_client = mqtt_client
        
        # Initialize parking spots (all available at start)
        self.spots = {
            f"SPOT_{i+1:03d}": {
                "occupied": False,
                "vehicle_type": None,
                "occupied_since": None,
                "sensor_id": f"{self.parking_lot_id}_SENSOR_{i+1:03d}"
            }
            for i in range(self.total_spots)
        }
        
        print(f"✅ Parking Lot IoT {self.parking_lot_id} initialized")
        print(f"   Location: {self.config['location']['address']}")
        print(f"   Zone: {self.config['location']['zone']}")
        print(f"   GPS: ({self.config['location']['gps']['latitude']}, {self.config['location']['gps']['longitude']})")
        print(f"   Total spots: {self.total_spots}")
        print(f"   Sensor type: {self.config['sensor_type']}")
        print(f"   Protocol: {self.config['protocol']}")
        if mqtt_client:
            print(f"   MQTT: ENABLED ✅")
    
    def _load_config(self, config_file):
        """Load parking lot configuration"""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def _get_time_factor(self):
        """
        Get parking demand based on time of day
        Returns multiplier for occupancy probability
        """
        hour = datetime.now().hour
        
        # Business hours (9 AM - 6 PM) = high demand
        if 9 <= hour <= 18:
            return 0.85  # 85% occupancy
        # Evening (6 PM - 10 PM) = medium demand
        elif 18 < hour <= 22:
            return 0.60  # 60% occupancy
        # Night (10 PM - 7 AM) = low demand
        elif 22 < hour or hour < 7:
            return 0.20  # 20% occupancy
        # Morning (7 AM - 9 AM) = rising demand
        else:
            return 0.50  # 50% occupancy
    
    def _simulate_parking_event(self):
        """
        Simulate random parking events (cars entering/leaving)
        Returns: list of events (state changes)
        """
        events = []
        target_occupancy = self._get_time_factor()
        current_occupancy = sum(1 for spot in self.spots.values() if spot['occupied']) / self.total_spots
        
        # Determine if we should add or remove cars
        if current_occupancy < target_occupancy:
            # Fill up parking lot
            num_events = random.randint(1, 3)
            for _ in range(num_events):
                # Find available spot
                available = [spot_id for spot_id, data in self.spots.items() if not data['occupied']]
                if available:
                    spot_id = random.choice(available)
                    vehicle_type = random.choice(['sedan', 'suv', 'truck', 'motorcycle', 'electric'])
                    
                    # Generate license plate FIRST (if enabled)
                    license_plate = None
                    if self.config.get('has_license_plate_recognition', False):
                        # Format: LUX-ABC-123 (Luxembourg style)
                        license_plate = f"LUX-{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))}-{''.join(random.choices('0123456789', k=3))}"
                    
                    # Car enters (THEN store it)
                    self.spots[spot_id]['occupied'] = True
                    self.spots[spot_id]['vehicle_type'] = vehicle_type
                    self.spots[spot_id]['occupied_since'] = datetime.now().isoformat()
                    self.spots[spot_id]['license_plate'] = license_plate  # Store it
                    
                    events.append({
                        "event_type": "vehicle_entered",
                        "spot_id": spot_id,
                        "vehicle_type": vehicle_type,
                        "license_plate": license_plate,
                        "timestamp": datetime.now().isoformat()
                    })
        
        elif current_occupancy > target_occupancy:
            # Empty out parking lot
            num_events = random.randint(1, 3)
            for _ in range(num_events):
                # Find occupied spot
                occupied = [spot_id for spot_id, data in self.spots.items() if data['occupied']]
                if occupied:
                    spot_id = random.choice(occupied)
                    
                    # Calculate duration (for analytics)
                    occupied_since = self.spots[spot_id]['occupied_since']
                    if occupied_since:
                        duration_seconds = (datetime.now() - datetime.fromisoformat(occupied_since)).total_seconds()
                    else:
                        duration_seconds = 0
                    
                    # Get license plate before clearing
                    license_plate = self.spots[spot_id].get('license_plate')
                    
                    # Car leaves
                    self.spots[spot_id]['occupied'] = False
                    vehicle_type = self.spots[spot_id]['vehicle_type']
                    self.spots[spot_id]['vehicle_type'] = None
                    self.spots[spot_id]['occupied_since'] = None
                    self.spots[spot_id]['license_plate'] = None  # Clear it
                    
                    events.append({
                        "event_type": "vehicle_exited",
                        "spot_id": spot_id,
                        "vehicle_type": vehicle_type,
                        "license_plate": license_plate,
                        "duration_minutes": round(duration_seconds / 60, 1),
                        "timestamp": datetime.now().isoformat()
                    })
        
        return events
    
    def get_status_packet(self):
        """
        Generate parking lot status packet
        This is sent periodically (every 30-60 seconds)
        """
        occupied_count = sum(1 for spot in self.spots.values() if spot['occupied'])
        available_count = self.total_spots - occupied_count
        occupancy_rate = round(occupied_count / self.total_spots, 2)
        
        # Count by vehicle type
        vehicle_types = {}
        for spot in self.spots.values():
            if spot['occupied'] and spot['vehicle_type']:
                vehicle_types[spot['vehicle_type']] = vehicle_types.get(spot['vehicle_type'], 0) + 1
        
        packet = {
            "device_type": "parking_iot_sensor",
            "protocol": self.config['protocol'],
            "parking_lot_id": self.parking_lot_id,
            "parking_lot_name": self.config['parking_lot_name'],
            "timestamp": datetime.now().isoformat(),
            
            # Location
            "location": self.config['location'],
            
            # Occupancy data
            "occupancy": {
                "total_spots": self.total_spots,
                "occupied_spots": occupied_count,
                "available_spots": available_count,
                "occupancy_rate": occupancy_rate,
                "status": "full" if occupancy_rate >= 0.95 else "high" if occupancy_rate >= 0.80 else "medium" if occupancy_rate >= 0.50 else "low"
            },
            
            # Vehicle breakdown
            "vehicle_breakdown": vehicle_types,
            
            # Pricing (dynamic based on demand)
            "pricing": {
                "current_rate_per_hour": round(self.config['base_rate'] * (1 + occupancy_rate * 0.5), 2),
                "currency": "EUR"
            },
            
            # Sensor status
            "sensor_status": {
                "online_sensors": self.total_spots,
                "offline_sensors": 0,
                "battery_low": random.randint(0, 2)
            }
        }
        
        return packet
    
    def get_event_packet(self, event):
        """
        Generate event packet for state change
        Sent immediately when car enters/exits
        """
        packet = {
            "device_type": "parking_iot_sensor",
            "protocol": self.config['protocol'],
            "parking_lot_id": self.parking_lot_id,
            "timestamp": datetime.now().isoformat(),
            "location": self.config['location'],
            "event": event
        }
        
        return packet
    
    def _publish_packet(self, packet, topic_suffix):
        """
        Publish packet via MQTT or print to stdout
        """
        # Print to console (always)
        print(json.dumps(packet, indent=2))
        print("-" * 80)
        
        # Publish to MQTT if available
        if self.mqtt_client:
            topic = f"parking/{self.parking_lot_id}/{topic_suffix}"
            payload = json.dumps(packet)
            self.mqtt_client.publish(topic, payload)
            print(f"📡 Published to MQTT: {topic}")
            print("-" * 80)
    
    def stream(self, status_interval=30, event_probability=0.3):
        """
        Run parking lot IoT simulation
        
        Args:
            status_interval: Seconds between status updates
            event_probability: Probability of parking event per cycle (0-1)
        """
        print(f"\n🅿️  Starting Parking IoT: {self.parking_lot_id}")
        print(f"   Status updates every {status_interval} seconds")
        print(f"   Event-based updates on state changes")
        print(f"   Press Ctrl+C to stop\n")
        
        last_status_time = time.time()
        
        try:
            while True:
                current_time = time.time()
                
                # 1. Check for parking events (cars entering/leaving)
                if random.random() < event_probability:
                    events = self._simulate_parking_event()
                    
                    for event in events:
                        # Send event packet immediately
                        event_packet = self.get_event_packet(event)
                        self._publish_packet(event_packet, "event")
                
                # 2. Send periodic status update
                if current_time - last_status_time >= status_interval:
                    status_packet = self.get_status_packet()
                    self._publish_packet(status_packet, "status")
                    last_status_time = current_time
                
                # Wait before next cycle
                time.sleep(5)  # Check every 5 seconds
        
        except KeyboardInterrupt:
            print(f"\n🛑 Parking IoT stopped: {self.parking_lot_id}")
            
            # Final summary
            occupied = sum(1 for spot in self.spots.values() if spot['occupied'])
            print(f"   Final occupancy: {occupied}/{self.total_spots} ({occupied/self.total_spots*100:.1f}%)")


def main():
    """
    Main function - runs all parking lot IoT simulators with MQTT
    """
    import sys
    import multiprocessing
    
    # Setup MQTT client
    mqtt_client = None
    if MQTT_AVAILABLE:
        print("🔌 Connecting to MQTT Broker...")
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        try:
            mqtt_client.connect("localhost", 1883, 60)
            mqtt_client.loop_start()
            print("✅ Connected to MQTT (localhost:1883)")
        except Exception as e:
            print(f"⚠️  MQTT connection failed: {e}")
            print("   Continuing without MQTT (JSON output only)")
            mqtt_client = None
    
    print("")
    
    # Get all parking lot config files
    config_dir = Path("parking_lots")
    
    if not config_dir.exists():
        print("❌ Error: 'parking_lots/' folder not found")
        print("   Create: parking_lots/lot_001_config.json")
        sys.exit(1)
    
    config_files = list(config_dir.glob("*_config.json"))
    
    if not config_files:
        print("❌ Error: No parking lot configs found")
        sys.exit(1)
    
    print(f"🅿️  Found {len(config_files)} parking lots")
    print("="*80)
    
    # Initialize all parking lots
    parking_lots = []
    for config_file in sorted(config_files):
        try:
            lot = ParkingLotIoT(config_file, mqtt_client)
            parking_lots.append(lot)
        except Exception as e:
            print(f"❌ Failed to load {config_file.name}: {e}")
    
    if not parking_lots:
        print("❌ No parking lots could be initialized")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("🚀 Starting Parking IoT simulation...")
    print("   Protocol: LoRaWAN (via MQTT)")
    print("   Event-based + periodic updates")
    print("   This is ONLY IoT device simulation")
    if mqtt_client:
        print("   📡 Publishing to MQTT topics: parking/{lot_id}/{event|status}")
    print(f"   Running {len(parking_lots)} parking lot(s) simultaneously")
    print("="*80 + "\n")
    
    # Run ALL parking lots simultaneously in separate processes
    processes = []
    
    try:
        for lot in parking_lots:
            # Each parking lot runs in its own process
            p = multiprocessing.Process(target=lot.stream, kwargs={
                'status_interval': 30,
                'event_probability': 0.3
            })
            p.start()
            processes.append(p)
            print(f"✅ Started process for {lot.parking_lot_id}")
        
        print(f"\n🔥 All {len(processes)} parking lots running!")
        print("   Press Ctrl+C to stop all\n")
        
        # Wait for all processes
        for p in processes:
            p.join()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all parking lots...")
        for p in processes:
            p.terminate()
            p.join()
        print("✅ All parking lots stopped")
    finally:
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()


if __name__ == "__main__":
    main()