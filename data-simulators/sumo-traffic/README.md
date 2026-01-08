# 🚗 SUMO Traffic Simulator Connector

Connects to SUMO traffic simulation via TraCI API and streams comprehensive vehicle data to MQTT in real-time.

## 🎯 What This Does

- Connects to **SUMO simulation** (LuST Luxembourg scenario)
- Extracts **real-time traffic data** via TraCI API
- Publishes to **MQTT** every 5 seconds
- Monitors **roads, vehicles, traffic lights, and simulation stats**

## 📁 Project Structure

```
sumo-traffic/
├── sumo_mqtt_connector.py    # Main connector script
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🔧 Setup

### Prerequisites

- ✅ SUMO and LuST scenario installed
- ✅ Python 3.7+ with pip
- ✅ MQTT broker (mosquitto) running

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
paho-mqtt==1.6.1
```

### Verify MQTT Broker

```bash
# Check if mosquitto is running
sudo systemctl status mosquitto

# If not running, start it
sudo systemctl start mosquitto
```

## 🚀 Quick Start

### Step 1: Start MQTT Subscriber (IMPORTANT: Do this FIRST!)

```bash
# Start subscriber and leave it running
mosquitto_sub -h localhost -t 'traffic/sumo/#' -v
```

> **💡 Tip:** MQTT messages are NOT stored. Start the subscriber before the connector to see data in real-time.

### Step 2: Start SUMO with TraCI

```bash
cd ~/Downloads/firefox-install/BigData/simulators/LuST/LuSTScenario/scenario

# With GUI (visual):
sumo-gui -c dua.actuated.sumocfg --remote-port 8813

# Without GUI (faster):
sumo -c dua.actuated.sumocfg --remote-port 8813
```

Click "Play" button in SUMO GUI (or simulation starts automatically in CLI mode)

### Step 3: Run Connector

```bash
cd sumo-traffic
python sumo_mqtt_connector.py
```

You should immediately see data flowing in Terminal 1 (subscriber)! 🎉

## 📡 MQTT Topics & Data

### Topic Structure

The connector publishes to multiple topic hierarchies:

```
traffic/sumo/
├── edges/{edge_id}              → Road/segment traffic data
├── vehicles/{vehicle_id}        → Individual vehicle tracking
├── traffic_lights/{light_id}    → Traffic light states
└── simulation/stats             → Overall simulation statistics
```

### 1. Edge/Road Traffic Data

**Topic:** `traffic/sumo/edges/{edge_id}`

```json
{
  "device_type": "sumo_edge_sensor",
  "protocol": "TraCI/MQTT",
  "edge_id": "-31606#0",
  "timestamp": "2026-01-08T03:20:12",
  "simulation_time": 125.0,
  "traffic_data": {
    "vehicle_count": 15,
    "average_speed_kmh": 45.3,
    "lane_occupancy": 0.65,
    "congestion_level": "medium",
    "vehicle_types": {
      "passenger": 12,
      "bus": 2,
      "truck": 1
    }
  }
}
```

### 2. Individual Vehicle Data

**Topic:** `traffic/sumo/vehicles/{vehicle_id}`

```json
{
  "device_type": "sumo_vehicle_tracker",
  "protocol": "TraCI/MQTT",
  "vehicle_id": "vehicle_123",
  "timestamp": "2026-01-08T03:20:12",
  "simulation_time": 125.0,
  "vehicle_info": {
    "type": "passenger2a",
    "vehicle_class": "passenger"
  },
  "location": {
    "position": {"x": 6648.42, "y": 6021.03},
    "road_id": "-31606#0",
    "lane_id": "-31606#0_1",
    "lane_position": 52.3
  },
  "dynamics": {
    "speed_kmh": 52.1,
    "acceleration": 0.5,
    "max_speed_kmh": 180.0
  },
  "route": {
    "current_route": ["-31606#0", "-31606#1", "..."],
    "destination": "-31366#3"
  },
  "emissions": {
    "co2_mg_s": 2671.52,
    "co_mg_s": 12.98,
    "nox_mg_s": 0.96,
    "fuel_ml_s": 866.08
  },
  "traffic_state": {
    "waiting_time_s": 0.0
  }
}
```

### 3. Traffic Light States

**Topic:** `traffic/sumo/traffic_lights/{light_id}`

```json
{
  "device_type": "sumo_traffic_light",
  "protocol": "TraCI/MQTT",
  "traffic_light_id": "-10130",
  "timestamp": "2026-01-08T03:20:12",
  "simulation_time": 125.0,
  "traffic_light_state": {
    "state": "GGrrGGrr",
    "phase": 0,
    "next_switch_time": 30.0
  }
}
```

> **State codes:** `G` = green, `r` = red, `y` = yellow

### 4. Simulation Statistics

**Topic:** `traffic/sumo/simulation/stats`

```json
{
  "device_type": "sumo_simulation_stats",
  "protocol": "TraCI/MQTT",
  "timestamp": "2026-01-08T03:20:12",
  "simulation_time": 125.0,
  "statistics": {
    "vehicles_departed": 1250,
    "vehicles_arrived": 850,
    "vehicles_current": 400,
    "vehicles_loaded": 2500
  }
}
```

## 🎲 What Gets Monitored

### Road-Level Metrics
- **Vehicle count** per road segment
- **Average speed** (km/h)
- **Lane occupancy** (0-1, road capacity usage)
- **Congestion level** (low/medium/high)
- **Vehicle type breakdown** (passenger, bus, truck)

### Vehicle-Level Metrics
- **Position** (x, y coordinates + road/lane ID)
- **Speed & acceleration**
- **Route & destination**
- **Emissions** (CO₂, CO, NOₓ, fuel consumption)
- **Waiting time** (time stopped in traffic)

### Traffic Light States
- **Current phase** (green/yellow/red configuration)
- **Next switch time**

### Congestion Detection

| Level | Criteria |
|-------|----------|
| **High** | Occupancy > 80% OR speed < 20 km/h |
| **Medium** | Occupancy > 50% OR speed < 40 km/h |
| **Low** | Otherwise |

## ⚙️ Configuration

Edit the `main()` function in `sumo_mqtt_connector.py`:

```python
connector.run(
    interval=5,                    # Update every N seconds (1-60)
    sample_edges=20,               # Monitor N road segments (-1 for all)
    sample_vehicles=10,            # Track N vehicles (-1 for all, 0 to disable)
    include_traffic_lights=True    # Monitor traffic lights
)
```

### Configuration Examples

**High-frequency monitoring (1-second updates):**
```python
connector.run(interval=1, sample_edges=50, sample_vehicles=20)
```

**Monitor everything (warning: high data volume):**
```python
connector.run(interval=5, sample_edges=-1, sample_vehicles=-1, include_traffic_lights=True)
```

**Roads only (no vehicle tracking):**
```python
connector.run(interval=10, sample_edges=30, sample_vehicles=0, include_traffic_lights=False)
```

## 🔧 System Architecture

```
┌─────────────────────┐
│  SUMO Simulation    │
│  (LuST Scenario)    │
└──────────┬──────────┘
           │ TraCI API (TCP :8813)
           ↓
┌─────────────────────┐
│  Python Connector   │
│  (This Script)      │
└──────────┬──────────┘
           │ MQTT Protocol (:1883)
           ↓
┌─────────────────────┐
│  MQTT Broker        │
│  (mosquitto)        │
└──────────┬──────────┘
           │
           ├──→ Kafka Pipeline
           ├──→ Data Processing
           └──→ Analytics/Visualization
```

## 🧪 Testing & Monitoring

### Listen to Specific Data Types

```bash
# All SUMO data
mosquitto_sub -h localhost -t 'traffic/sumo/#' -v

# Road traffic only
mosquitto_sub -h localhost -t 'traffic/sumo/edges/#' -v

# Vehicle tracking only
mosquitto_sub -h localhost -t 'traffic/sumo/vehicles/#' -v

# Traffic lights only
mosquitto_sub -h localhost -t 'traffic/sumo/traffic_lights/#' -v

# Simulation stats only
mosquitto_sub -h localhost -t 'traffic/sumo/simulation/stats' -v
```

### Count Messages

```bash
# Receive exactly 10 messages then stop
mosquitto_sub -h localhost -t 'traffic/sumo/#' -C 10
```

### Test MQTT Broker

```bash
# Terminal 1: Subscribe
mosquitto_sub -h localhost -t 'test/topic' -v

# Terminal 2: Publish
mosquitto_pub -h localhost -t 'test/topic' -m 'Hello MQTT!'

# Should see "Hello MQTT!" in Terminal 1
```

## ⚠️ Troubleshooting

### Connection Refused (TraCI)

**Problem:** `❌ Failed to connect to SUMO`

**Solutions:**
- Ensure SUMO is running with `--remote-port 8813`
- Start SUMO **before** the connector
- Check if port 8813 is already in use: `netstat -tulpn | grep 8813`

### No Data in Subscriber

**Problem:** `mosquitto_sub` shows nothing

**Solutions:**
1. **Start subscriber BEFORE connector** (MQTT doesn't store messages)
2. Check MQTT broker is running: `sudo systemctl status mosquitto`
3. Test with wildcard: `mosquitto_sub -h localhost -t '#' -v`
4. Verify connector shows `✅ Published to:` messages

### Simulation Ended

**Problem:** Connector stops with "Simulation ended"

**Solutions:**
- SUMO simulation finished naturally
- Click "Reload" in SUMO GUI
- Or restart SUMO from command line

### No Vehicles in Data

**Problem:** Only traffic light/stats data, no vehicles

**Solutions:**
- Roads might be empty at simulation start
- Let SUMO run for 30-60 seconds
- Check vehicles are spawning in SUMO GUI
- Verify `sample_vehicles` is not set to `0`

### MQTT Connection Failed

**Problem:** `⚠️ Failed to connect to MQTT`

**Solutions:**
```bash
# Check if mosquitto is installed
which mosquitto

# Install if missing (Ubuntu/Debian)
sudo apt-get install mosquitto mosquitto-clients

# Start mosquitto
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Check it's running
sudo systemctl status mosquitto
```

## 🛑 Stopping the System

### Stop Connector
Press **Ctrl+C** in the connector terminal

### Stop SUMO
Close SUMO GUI or press **Ctrl+C** in CLI mode

### Stop MQTT Subscriber
Press **Ctrl+C** in subscriber terminal

> **Note:** SUMO simulation will keep running independently. Always close it manually.

## 📍 LuST Scenario Details

Uses **Luxembourg SUMO Traffic (LuST)** scenario:
- 📍 **19,027 road segments** (entire Luxembourg City)
- 🚗 **Realistic traffic patterns** based on real data
- 🚌 **Multiple vehicle types** (cars, buses, trucks, motorcycles)
- 🗺️ **Real road network** from OpenStreetMap
- ⏱️ **24-hour simulation** capability

## 📊 Performance Notes

### Data Volume Estimates

| Configuration | Messages/5sec | Data Rate | Daily Volume |
|--------------|---------------|-----------|--------------|
| Default (20 roads + 10 vehicles) | ~16 | ~50 KB/s | ~4 GB/day |
| All roads (-1) | ~200+ | ~500 KB/s | ~40 GB/day |
| All vehicles (-1) | ~1000+ | ~2 MB/s | ~170 GB/day |

> **⚠️ Warning:** Monitoring all roads and vehicles generates significant data. Use sampling for production deployments.

## 🔗 Integration

This connector is designed to work with:
- **Apache Kafka** (via MQTT-Kafka bridge)
- **Apache Spark** (streaming analytics)
- **Time-series databases** (InfluxDB, TimescaleDB)
- **Real-time dashboards** (Grafana, Kibana)

## 📝 License

Part of the Smart City Data Pipeline project.

---

**Status:** ✅ Working | **Protocol:** TraCI → MQTT | **Update:** Every 5 seconds | **Last Updated:** 2026-01-08