#!/usr/bin/env python3
"""
Smart City - Air Quality IoT Simulator
Simulates air quality monitoring stations
Sends data via MQTT protocol (continuous monitoring)
"""

import json
import time
import random
from datetime import datetime
from pathlib import Path
import math

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("⚠️  paho-mqtt not installed. Install with: pip install paho-mqtt")


class AirQualitySensor:
    """
    Simulates air quality monitoring station
    Measures: PM2.5, PM10, NO2, CO, O3, SO2
    Sends periodic updates via MQTT
    """
    
    def __init__(self, config_file, mqtt_client=None):
        self.config = self._load_config(config_file)
        self.sensor_id = self.config['sensor_id']
        self.mqtt_client = mqtt_client
        
        # Initialize baseline pollution levels
        self.baseline = {
            'pm25': 20.0,   # μg/m³
            'pm10': 35.0,   # μg/m³
            'no2': 25.0,    # ppb
            'co': 0.5,      # ppm
            'o3': 40.0,     # ppb
            'so2': 5.0      # ppb
        }
        
        print(f"✅ Air Quality Sensor {self.sensor_id} initialized")
        print(f"   Location: {self.config['location']['address']}")
        print(f"   Zone: {self.config['location']['zone']}")
        print(f"   GPS: ({self.config['location']['gps']['latitude']}, {self.config['location']['gps']['longitude']})")
        print(f"   Sensor type: {self.config['sensor_type']}")
        print(f"   Protocol: {self.config['protocol']}")
        if mqtt_client:
            print(f"   MQTT: ENABLED ✅")
    
    def _load_config(self, config_file):
        """Load sensor configuration"""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def _get_traffic_factor(self):
        """
        Get traffic pollution factor based on time of day
        Higher traffic = more pollution (NO2, CO, PM)
        """
        hour = datetime.now().hour
        
        # Rush hours = high pollution
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            return 1.8  # 80% increase
        # Business hours = medium pollution
        elif 9 < hour < 17:
            return 1.3  # 30% increase
        # Night = low pollution
        elif 22 <= hour or hour <= 6:
            return 0.6  # 40% decrease
        # Other times
        else:
            return 1.0  # baseline
    
    def _get_weather_factor(self):
        """
        Simulate weather impact on air quality
        Rain = lower pollution, hot sunny days = higher ozone
        """
        # Simple simulation - in real system, integrate with weather API
        hour = datetime.now().hour
        
        # Afternoon sun = more ozone
        if 12 <= hour <= 16:
            return {'ozone_mult': 1.5, 'pm_mult': 0.9}
        # Night/morning = stable
        else:
            return {'ozone_mult': 0.8, 'pm_mult': 1.0}
    
    def _calculate_aqi(self, pm25):
        """
        Calculate Air Quality Index from PM2.5
        Based on EPA standard
        """
        if pm25 <= 12.0:
            # Good (0-50)
            return int((50 / 12.0) * pm25), "Good", "Air quality is satisfactory"
        elif pm25 <= 35.4:
            # Moderate (51-100)
            return int(50 + ((50 / 23.4) * (pm25 - 12.0))), "Moderate", "Acceptable for most people"
        elif pm25 <= 55.4:
            # Unhealthy for Sensitive Groups (101-150)
            return int(100 + ((50 / 20.0) * (pm25 - 35.4))), "Unhealthy for Sensitive Groups", "Sensitive groups should reduce outdoor exposure"
        elif pm25 <= 150.4:
            # Unhealthy (151-200)
            return int(150 + ((50 / 95.0) * (pm25 - 55.4))), "Unhealthy", "Everyone may experience health effects"
        elif pm25 <= 250.4:
            # Very Unhealthy (201-300)
            return int(200 + ((100 / 100.0) * (pm25 - 150.4))), "Very Unhealthy", "Health alert: everyone may experience serious effects"
        else:
            # Hazardous (301-500)
            return int(300 + ((200 / 249.6) * min(pm25 - 250.4, 249.6))), "Hazardous", "Health warning: emergency conditions"
    
    def generate_measurement(self):
        """
        Generate realistic air quality measurement
        Considers time of day, traffic, weather
        """
        traffic_factor = self._get_traffic_factor()
        weather_factor = self._get_weather_factor()
        
        # Add random fluctuations
        noise = lambda: random.uniform(0.9, 1.1)
        
        # Pollutants affected by traffic
        pm25 = self.baseline['pm25'] * traffic_factor * weather_factor['pm_mult'] * noise()
        pm10 = self.baseline['pm10'] * traffic_factor * weather_factor['pm_mult'] * noise()
        no2 = self.baseline['no2'] * traffic_factor * noise()
        co = self.baseline['co'] * traffic_factor * noise()
        
        # Ozone (inverse to NO2, affected by sunlight)
        o3 = self.baseline['o3'] * weather_factor['ozone_mult'] * (2.0 - traffic_factor) * noise()
        
        # SO2 (industrial, less variable)
        so2 = self.baseline['so2'] * noise()
        
        # Calculate AQI
        aqi, aqi_category, health_advisory = self._calculate_aqi(pm25)
        
        # Environmental conditions
        temperature = 15 + (10 * math.sin((datetime.now().hour - 6) * math.pi / 12))  # Sine wave 10-25°C
        humidity = 60 + random.uniform(-10, 10)
        
        packet = {
            "device_type": "air_quality_sensor",
            "protocol": self.config['protocol'],
            "sensor_id": self.sensor_id,
            "sensor_name": self.config['sensor_name'],
            "timestamp": datetime.now().isoformat(),
            
            # Location
            "location": self.config['location'],
            
            # Air quality measurements
            "measurements": {
                "pm25": round(pm25, 1),
                "pm10": round(pm10, 1),
                "no2": round(no2, 1),
                "co": round(co, 2),
                "o3": round(o3, 1),
                "so2": round(so2, 1),
                "temperature_celsius": round(temperature, 1),
                "humidity_percent": round(humidity, 1)
            },
            
            # Air Quality Index
            "aqi": {
                "value": aqi,
                "category": aqi_category,
                "health_advisory": health_advisory
            },
            
            # Sensor status
            "sensor_status": {
                "online": True,
                "calibration_date": "2025-12-01",
                "battery_percent": random.randint(85, 100),
                "signal_strength": random.randint(70, 100)
            }
        }
        
        return packet
    
    def _publish_packet(self, packet):
        """
        Publish packet via MQTT or print to stdout
        """
        # Print to console (always)
        print(json.dumps(packet, indent=2))
        print("-" * 80)
        
        # Publish to MQTT if available
        if self.mqtt_client:
            topic = f"air_quality/{self.sensor_id}/data"
            payload = json.dumps(packet)
            self.mqtt_client.publish(topic, payload)
            print(f"📡 Published to MQTT: {topic}")
            print("-" * 80)
    
    def stream(self, interval=300):
        """
        Run air quality monitoring (continuous)
        
        Args:
            interval: Seconds between measurements (default: 300s = 5 min)
        """
        print(f"\n🌫️  Starting Air Quality Monitor: {self.sensor_id}")
        print(f"   Measurements every {interval} seconds ({interval//60} minutes)")
        print(f"   Press Ctrl+C to stop\n")
        
        measurement_count = 0
        
        try:
            while True:
                # Generate measurement
                packet = self.generate_measurement()
                self._publish_packet(packet)
                
                measurement_count += 1
                
                # Wait before next measurement
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print(f"\n🛑 Air Quality Monitor stopped: {self.sensor_id}")
            print(f"   Total measurements: {measurement_count}")


def main():
    """
    Main function - runs all air quality sensors with MQTT
    """
    import sys
    import multiprocessing
    
    # DON'T create MQTT client here for multiprocessing
    # Each process will create its own
    
    # Get all sensor config files
    config_dir = Path("air_quality_sensors")
    
    if not config_dir.exists():
        print("❌ Error: 'air_quality_sensors/' folder not found")
        print("   Create: air_quality_sensors/sensor_001_config.json")
        sys.exit(1)
    
    config_files = list(config_dir.glob("*_config.json"))
    
    if not config_files:
        print("❌ Error: No sensor configs found")
        sys.exit(1)
    
    print(f"🌫️  Found {len(config_files)} air quality sensors")
    print("="*80)
    
    print("\n" + "="*80)
    print("🚀 Starting Air Quality monitoring...")
    print("   Protocol: MQTT")
    print("   Continuous monitoring (every 5 minutes)")
    print("   This is ONLY IoT device simulation")
    print("   📡 Publishing to MQTT topics: air_quality/{sensor_id}/data")
    print(f"   Running {len(config_files)} sensor(s) simultaneously")
    print("="*80 + "\n")
    
    # Helper function to run sensor in separate process
    def run_sensor(config_file):
        """Each process creates its own MQTT client"""
        mqtt_client = None
        if MQTT_AVAILABLE:
            try:
                mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                mqtt_client.connect("localhost", 1883, 60)
                mqtt_client.loop_start()
            except:
                mqtt_client = None
        
        sensor = AirQualitySensor(config_file, mqtt_client)
        try:
            sensor.stream(interval=300)  # 5 minutes
        finally:
            if mqtt_client:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
    
    # Run ALL sensors simultaneously in separate processes
    processes = []
    
    try:
        for config_file in sorted(config_files):
            p = multiprocessing.Process(target=run_sensor, args=(config_file,))
            p.start()
            processes.append(p)
            print(f"✅ Started process for {config_file.stem}")
        
        print(f"\n🔥 All {len(processes)} sensors running!")
        print("   Press Ctrl+C to stop all\n")
        
        # Wait for all processes
        for p in processes:
            p.join()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all sensors...")
        for p in processes:
            p.terminate()
            p.join()
        print("✅ All sensors stopped")


if __name__ == "__main__":
    main()