# 🌫️ Air Quality IoT Sensor Simulator

Simulates real air quality monitoring stations with MQTT protocol.

## 🎯 What This Does

- Simulates **multi-gas particulate sensors** (PM2.5, PM10, NO2, CO, O3, SO2)
- Sends continuous measurements via **MQTT** every 5 minutes
- Calculates **Air Quality Index (AQI)** based on EPA standards
- Realistic pollution patterns (correlates with traffic, time of day, weather)

## 📁 Structure

```
air-quality-sensors/
├── air_quality_sensors/
│   ├── sensor_001_config.json    # Downtown station
│   └── sensor_002_config.json    # Industrial zone
├── air_quality_simulator.py      # Main simulator
└── requirements.txt
```

## 🔧 Setup

### 1. Install MQTT Broker (if not already installed)

```bash
chmod +x setup_mqtt.sh
./setup_mqtt.sh
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
paho-mqtt==1.6.1
```

## 🚀 Run Simulator

```bash
# Start simulator (runs all sensors)
python air_quality_simulator.py
```

**In another terminal, monitor MQTT:**
```bash
mosquitto_sub -h localhost -t 'air_quality/#' -v
```

## 📡 Why MQTT?

| Feature | Why? |
|---------|------|
| **Reliable** | TCP-based, guaranteed delivery |
| **Efficient** | Low bandwidth for periodic updates |
| **Powered** | Sensors connected to mains electricity |
| **Standard** | Used by most air quality networks |

**NOT LoRaWAN because:** Air quality sensors send data every 5 minutes (too frequent for LoRaWAN). They're also mains-powered, so battery life isn't a concern.

**Used by:** PurpleAir, Airly, Breezometer for urban air quality monitoring.

## 📊 Data Output

**Topic:** `air_quality/{sensor_id}/data`

**Update Frequency:** Every 5 minutes (300 seconds)

```json
{
  "device_type": "air_quality_sensor",
  "protocol": "MQTT",
  "sensor_id": "AQ_LUX_001",
  "sensor_name": "Centre Ville Air Quality Station",
  "timestamp": "2026-01-08T14:30:00",
  "location": {
    "gps": {"latitude": 49.6116, "longitude": 6.1319},
    "city": "Luxembourg City",
    "zone": "downtown",
    "address": "Boulevard Royal, Luxembourg"
  },
  "measurements": {
    "pm25": 35.2,           // μg/m³ (fine particles)
    "pm10": 52.8,           // μg/m³ (coarse particles)
    "no2": 28.5,            // ppb (nitrogen dioxide)
    "co": 0.8,              // ppm (carbon monoxide)
    "o3": 45.3,             // ppb (ozone)
    "so2": 5.2,             // ppb (sulfur dioxide)
    "temperature_celsius": 18.5,
    "humidity_percent": 65.3
  },
  "aqi": {
    "value": 72,
    "category": "Moderate",
    "health_advisory": "Acceptable for most people"
  },
  "sensor_status": {
    "online": true,
    "calibration_date": "2025-12-01",
    "battery_percent": 95,
    "signal_strength": 87
  }
}
```

## 📈 Air Quality Index (AQI)

Based on EPA standard:

| AQI | Category | Health Impact | Color |
|-----|----------|---------------|-------|
| 0-50 | Good | Air quality is satisfactory | 🟢 Green |
| 51-100 | Moderate | Acceptable for most people | 🟡 Yellow |
| 101-150 | Unhealthy for Sensitive | Sensitive groups affected | 🟠 Orange |
| 151-200 | Unhealthy | Everyone may experience effects | 🔴 Red |
| 201-300 | Very Unhealthy | Health alert | 🟣 Purple |
| 301-500 | Hazardous | Emergency conditions | 🟤 Maroon |

## 🎲 Simulation Features

### Time-Based Pollution Patterns

- **7-9 AM & 5-7 PM** (rush hour): +80% pollution (NO2, CO, PM)
- **9 AM - 5 PM** (business hours): +30% pollution
- **10 PM - 6 AM** (night): -40% pollution (clean air)

### Realistic Pollutant Behavior

- **PM2.5/PM10**: Higher during traffic, affected by weather
- **NO2/CO**: Correlates with vehicle emissions (rush hour spikes)
- **O3 (Ozone)**: Inverse to traffic, peaks during sunny afternoons
- **SO2**: Industrial, less variable

### Weather Simulation

- **Sunny afternoon** (12-4 PM): Ozone increases +50%
- **Rain/wind**: Particulate matter decreases
- **Temperature**: Sine wave pattern (10-25°C daily cycle)

## 🏙️ Sensor Locations

| ID | Location | Type | Zone |
|----|----------|------|------|
| AQ_LUX_001 | Centre Ville (Downtown) | Urban Traffic | High pollution |
| AQ_LUX_002 | Cloche d'Or | Industrial Area | Moderate pollution |

## 🔧 Configuration

**Config format (JSON):**
```json
{
  "sensor_id": "AQ_LUX_001",
  "sensor_name": "Centre Ville Air Quality Station",
  "location": {
    "gps": {"latitude": 49.6116, "longitude": 6.1319},
    "city": "Luxembourg City",
    "zone": "downtown",
    "address": "Boulevard Royal, Luxembourg"
  },
  "sensor_type": "multi_gas_particulate",
  "protocol": "MQTT",
  "manufacturer": "Airly",
  "installed_date": "2024-06-15"
}
```

## ⏱️ Update Intervals

| Interval | Use Case |
|----------|----------|
| **300s (5 min)** ✅ | Standard (recommended) |
| 60s (1 min) | High-traffic areas, testing |
| 600s (10 min) | Low-priority areas |
| 900s (15 min) | Rural, battery-saving |

**Change in code:**
```python
sensor.stream(interval=300)  # 5 minutes (default)
```

## 🧪 Testing

```bash
# Terminal 1: Start simulator
python air_quality_simulator.py

# Terminal 2: Monitor all air quality data
mosquitto_sub -h localhost -t 'air_quality/#'

# Terminal 3: Monitor specific sensor
mosquitto_sub -h localhost -t 'air_quality/AQ_LUX_001/#'

# Terminal 4: Monitor only measurements (filter)
mosquitto_sub -h localhost -t 'air_quality/+/data' | grep -A 10 "measurements"
```

## 📊 Data Analysis Use Cases

Air quality data enables:
- **Health Alerts**: Notify sensitive groups when AQI > 100
- **Traffic Correlation**: Analyze pollution vs traffic volume
- **Policy Making**: Support for low-emission zones
- **Forecasting**: Predict air quality using ML models
- **Public Dashboards**: Real-time city air quality maps

## 🛑 Stop Simulator

Press **Ctrl+C** to stop all sensors gracefully.

## 🌍 Real-World Comparison

Our simulation matches real air quality networks:

| Network | Update Frequency | Pollutants | Protocol |
|---------|------------------|------------|----------|
| **PurpleAir** | 2 minutes | PM2.5, PM10 | MQTT/HTTP |
| **Airly** | 5 minutes | PM, NO2, O3 | MQTT |
| **Breezometer** | 1 hour | Full suite | API |
| **Our Simulator** | 5 minutes ✅ | Full suite | MQTT |

---

**Status:** ✅ Working | **Protocol:** MQTT | **Update:** Every 5 minutes | **Last Updated:** 2026-01-08