#!/usr/bin/env python3
"""
Smart City - SUMO TraCI to MQTT Connector (ENHANCED - FIXED)
Connects to running SUMO simulation via TraCI
Extracts comprehensive traffic data and publishes to MQTT

MQTT Topics:
- traffic/sumo/edges/{edge_id}          → Road/edge traffic data
- traffic/sumo/vehicles/{vehicle_id}    → Individual vehicle data
- traffic/sumo/traffic_lights/{tl_id}   → Traffic light states
- traffic/sumo/simulation/stats         → Simulation-wide statistics
"""

import json
import time
import sys
import os
from datetime import datetime

# Check if SUMO_HOME is set
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("❌ Please set SUMO_HOME environment variable")

try:
    import traci
    TRACI_AVAILABLE = True
except ImportError:
    print("❌ TraCI not found! Install SUMO properly")
    TRACI_AVAILABLE = False

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    print("⚠️  paho-mqtt not installed. Install with: pip install paho-mqtt")
    MQTT_AVAILABLE = False


class SUMOTrafficConnector:
    """
    Connects to SUMO simulation via TraCI
    Extracts comprehensive vehicle/traffic data
    Publishes to MQTT broker
    """
    
    def __init__(self, sumo_port=8813, mqtt_host="localhost", mqtt_port=1883):
        self.sumo_port = sumo_port
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_client = None
        self.edge_list = []
        self.traffic_light_list = []
        
        print("🚗 SUMO TraCI to MQTT Connector (ENHANCED)")
        print("=" * 80)
    
    def connect_sumo(self):
        """Connect to running SUMO simulation via TraCI"""
        print(f"\n🔌 Connecting to SUMO on port {self.sumo_port}...")
        
        try:
            traci.init(self.sumo_port)
            print("✅ Connected to SUMO!")
            
            # Get list of edges (roads)
            self.edge_list = traci.edge.getIDList()
            print(f"   Found {len(self.edge_list)} road segments")
            
            # Get list of traffic lights
            self.traffic_light_list = traci.trafficlight.getIDList()
            print(f"   Found {len(self.traffic_light_list)} traffic lights")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to SUMO: {e}")
            print("\n💡 Make sure SUMO is running with TraCI enabled:")
            print("   sumo-gui -c your_config.sumocfg --remote-port 8813")
            return False
    
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        if not MQTT_AVAILABLE:
            print("⚠️  MQTT not available, will print to console only")
            return False
        
        print(f"\n🔌 Connecting to MQTT Broker ({self.mqtt_host}:{self.mqtt_port})...")
        
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            print("✅ Connected to MQTT!")
            return True
            
        except Exception as e:
            print(f"⚠️  Failed to connect to MQTT: {e}")
            print("   Continuing without MQTT (console output only)")
            return False
    
    def get_edge_data(self, edge_id):
        """Extract comprehensive traffic data from edge"""
        try:
            vehicle_ids = traci.edge.getLastStepVehicleIDs(edge_id)
            vehicle_count = len(vehicle_ids)
            
            if vehicle_count == 0:
                return None
            
            # Traffic metrics
            avg_speed = traci.edge.getLastStepMeanSpeed(edge_id) * 3.6  # km/h
            occupancy = traci.edge.getLastStepOccupancy(edge_id)
            
            # Congestion
            if occupancy > 0.8 or avg_speed < 20:
                congestion = "high"
            elif occupancy > 0.5 or avg_speed < 40:
                congestion = "medium"
            else:
                congestion = "low"
            
            # Vehicle type breakdown
            vehicle_types = {}
            for veh_id in vehicle_ids:
                try:
                    veh_type = traci.vehicle.getVehicleClass(veh_id)
                    vehicle_types[veh_type] = vehicle_types.get(veh_type, 0) + 1
                except:
                    pass
            
            packet = {
                "device_type": "sumo_edge_sensor",
                "protocol": "TraCI/MQTT",
                "edge_id": edge_id,
                "timestamp": datetime.now().isoformat(),
                "simulation_time": traci.simulation.getTime(),
                "traffic_data": {
                    "vehicle_count": vehicle_count,
                    "average_speed_kmh": round(avg_speed, 1),
                    "lane_occupancy": round(occupancy, 2),
                    "congestion_level": congestion,
                    "vehicle_types": vehicle_types
                }
            }
            
            return packet
            
        except Exception as e:
            print(f"⚠️ Error getting edge data for {edge_id}: {e}")
            return None
    
    def get_vehicle_data(self, vehicle_id):
        """Extract comprehensive data for individual vehicle"""
        try:
            packet = {
                "device_type": "sumo_vehicle_tracker",
                "protocol": "TraCI/MQTT",
                "vehicle_id": vehicle_id,
                "timestamp": datetime.now().isoformat(),
                "simulation_time": traci.simulation.getTime(),
                
                # Vehicle identity
                "vehicle_info": {
                    "type": traci.vehicle.getTypeID(vehicle_id),
                    "vehicle_class": traci.vehicle.getVehicleClass(vehicle_id)
                },
                
                # Position & Movement
                "location": {
                    "position": {
                        "x": round(traci.vehicle.getPosition(vehicle_id)[0], 2),
                        "y": round(traci.vehicle.getPosition(vehicle_id)[1], 2)
                    },
                    "road_id": traci.vehicle.getRoadID(vehicle_id),
                    "lane_id": traci.vehicle.getLaneID(vehicle_id),
                    "lane_position": round(traci.vehicle.getLanePosition(vehicle_id), 2)
                },
                
                # Speed & Dynamics
                "dynamics": {
                    "speed_kmh": round(traci.vehicle.getSpeed(vehicle_id) * 3.6, 1),
                    "acceleration": round(traci.vehicle.getAcceleration(vehicle_id), 2),
                    "max_speed_kmh": round(traci.vehicle.getMaxSpeed(vehicle_id) * 3.6, 1)
                },
                
                # Route info
                "route": {
                    "current_route": traci.vehicle.getRoute(vehicle_id),
                    "destination": traci.vehicle.getRoute(vehicle_id)[-1] if traci.vehicle.getRoute(vehicle_id) else None
                },
                
                # Emissions
                "emissions": {
                    "co2_mg_s": round(traci.vehicle.getCO2Emission(vehicle_id), 2),
                    "co_mg_s": round(traci.vehicle.getCOEmission(vehicle_id), 2),
                    "nox_mg_s": round(traci.vehicle.getNOxEmission(vehicle_id), 2),
                    "fuel_ml_s": round(traci.vehicle.getFuelConsumption(vehicle_id), 2)
                },
                
                # Traffic conditions
                "traffic_state": {
                    "waiting_time_s": round(traci.vehicle.getWaitingTime(vehicle_id), 1)
                }
            }
            
            return packet
            
        except Exception as e:
            print(f"⚠️ Error getting vehicle data for {vehicle_id}: {e}")
            return None
    
    def get_traffic_light_data(self, tl_id):
        """Extract traffic light state data"""
        try:
            state = traci.trafficlight.getRedYellowGreenState(tl_id)
            phase = traci.trafficlight.getPhase(tl_id)
            next_switch = traci.trafficlight.getNextSwitch(tl_id)
            
            packet = {
                "device_type": "sumo_traffic_light",
                "protocol": "TraCI/MQTT",
                "traffic_light_id": tl_id,
                "timestamp": datetime.now().isoformat(),
                "simulation_time": traci.simulation.getTime(),
                
                "traffic_light_state": {
                    "state": state,  # e.g., "GGrrGGrr" (G=green, r=red, y=yellow)
                    "phase": phase,
                    "next_switch_time": round(next_switch, 1)
                }
            }
            
            return packet
            
        except Exception as e:
            print(f"⚠️ Error getting traffic light data for {tl_id}: {e}")
            return None
    
    def get_simulation_stats(self):
        """Get simulation-wide statistics"""
        try:
            packet = {
                "device_type": "sumo_simulation_stats",
                "protocol": "TraCI/MQTT",
                "timestamp": datetime.now().isoformat(),
                "simulation_time": traci.simulation.getTime(),
                
                "statistics": {
                    "vehicles_departed": traci.simulation.getDepartedNumber(),
                    "vehicles_arrived": traci.simulation.getArrivedNumber(),
                    "vehicles_current": traci.vehicle.getIDCount(),
                    "vehicles_loaded": traci.simulation.getLoadedNumber()
                }
            }
            
            return packet
            
        except Exception as e:
            print(f"⚠️ Error getting simulation stats: {e}")
            return None
    
    def publish_to_mqtt(self, packet, topic_suffix):
        """Publish data to MQTT with appropriate topic"""
        # DON'T sanitize the whole topic - only sanitize problematic characters in IDs
        # Keep the topic structure intact (traffic/sumo/...)
        topic = topic_suffix.replace('#', '_').replace('+', '_')
        
        # Publish to MQTT
        if self.mqtt_client:
            try:
                payload = json.dumps(packet)
                result = self.mqtt_client.publish(topic, payload)
                if result.rc == 0:
                    print(f"✅ Published to: {topic}")
                else:
                    print(f"❌ Failed to publish to: {topic} (code: {result.rc})")
            except Exception as e:
                print(f"❌ MQTT publish error: {e}")
    
    def run(self, interval=5, sample_edges=10, sample_vehicles=5, include_traffic_lights=True):
        """
        Main loop: Extract comprehensive traffic data and publish to MQTT
        
        Args:
            interval: Seconds between updates (default: 5)
            sample_edges: Number of road segments to monitor (-1 for all)
            sample_vehicles: Number of vehicles to track in detail (-1 for all, 0 to disable)
            include_traffic_lights: Whether to monitor traffic lights
        """
        print("\n" + "=" * 80)
        print("🚀 Starting SUMO → MQTT data stream (ENHANCED)...")
        print(f"   Update interval: {interval} seconds")
        print(f"   Monitoring: {sample_edges if sample_edges > 0 else 'all'} road segments")
        print(f"   Tracking: {sample_vehicles if sample_vehicles > 0 else 'all' if sample_vehicles == -1 else 'no'} vehicles")
        print(f"   Traffic lights: {'Yes' if include_traffic_lights else 'No'}")
        print(f"   Press Ctrl+C to stop")
        print("=" * 80 + "\n")
        
        print("📡 MQTT Topics:")
        print("   • traffic/sumo/edges/{edge_id}        → Road traffic data")
        print("   • traffic/sumo/vehicles/{vehicle_id}  → Vehicle tracking")
        print("   • traffic/sumo/traffic_lights/{tl_id} → Traffic light states")
        print("   • traffic/sumo/simulation/stats       → Simulation statistics")
        print("\n" + "=" * 80 + "\n")
        
        step_count = 0
        last_publish_step = -interval  # Force first publish
        
        try:
            while traci.simulation.getMinExpectedNumber() > 0:
                # Advance simulation by 1 step
                traci.simulationStep()
                step_count += 1
                
                # Check if it's time to publish (every 'interval' steps)
                if step_count - last_publish_step >= interval:
                    last_publish_step = step_count
                    
                    print(f"\n{'='*80}")
                    print(f"📊 Publishing data at simulation time: {traci.simulation.getTime():.1f}s (step {step_count})")
                    print(f"{'='*80}\n")
                    
                    publish_count = 0
                    
                    # 1. Edge/Road data
                    edges_to_monitor = self.edge_list if sample_edges == -1 else self.edge_list[:sample_edges]
                    for edge_id in edges_to_monitor:
                        packet = self.get_edge_data(edge_id)
                        if packet:
                            topic = f"traffic/sumo/edges/{edge_id}"
                            self.publish_to_mqtt(packet, topic)
                            publish_count += 1
                    
                    # 2. Vehicle tracking
                    if sample_vehicles != 0:
                        all_vehicles = traci.vehicle.getIDList()
                        vehicles_to_track = all_vehicles if sample_vehicles == -1 else all_vehicles[:sample_vehicles]
                        
                        for veh_id in vehicles_to_track:
                            packet = self.get_vehicle_data(veh_id)
                            if packet:
                                topic = f"traffic/sumo/vehicles/{veh_id}"
                                self.publish_to_mqtt(packet, topic)
                                publish_count += 1
                    
                    # 3. Traffic lights
                    if include_traffic_lights and len(self.traffic_light_list) > 0:
                        # Sample 5 traffic lights
                        for tl_id in self.traffic_light_list[:5]:
                            packet = self.get_traffic_light_data(tl_id)
                            if packet:
                                topic = f"traffic/sumo/traffic_lights/{tl_id}"
                                self.publish_to_mqtt(packet, topic)
                                publish_count += 1
                    
                    # 4. Simulation stats
                    packet = self.get_simulation_stats()
                    if packet:
                        topic = "traffic/sumo/simulation/stats"
                        self.publish_to_mqtt(packet, topic)
                        publish_count += 1
                    
                    print(f"\n📈 Published {publish_count} messages")
                    print(f"⏱️  Simulation time: {traci.simulation.getTime():.1f}s")
                    print(f"🚗 Active vehicles: {traci.vehicle.getIDCount()}")
                    print(f"{'='*80}\n")
        
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping SUMO connector...")
        
        except Exception as e:
            print(f"\n❌ Error in main loop: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            print(f"\n📊 Statistics:")
            print(f"   Total simulation steps: {step_count}")
            print(f"   Total time: {step_count} seconds")
            
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            try:
                traci.close()
            except:
                pass
            
            print("\n✅ Disconnected from SUMO and MQTT")


def main():
    """Main function"""
    
    if not TRACI_AVAILABLE:
        sys.exit("❌ TraCI not available. Install SUMO and set SUMO_HOME")
    
    connector = SUMOTrafficConnector(
        sumo_port=8813,
        mqtt_host="localhost",
        mqtt_port=1883
    )
    
    if not connector.connect_sumo():
        sys.exit(1)
    
    connector.connect_mqtt()
    
    # Start streaming with comprehensive data
    connector.run(
        interval=5,                    # Update every 5 seconds
        sample_edges=20,               # Monitor 20 road segments (-1 for all)
        sample_vehicles=10,            # Track 10 vehicles in detail (-1 for all, 0 to disable)
        include_traffic_lights=True    # Include traffic light data
    )


if __name__ == "__main__":
    main()