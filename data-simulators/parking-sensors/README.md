# 🅿️ Parking Lot IoT Sensor Simulator

Simulates real parking sensors with LoRaWAN/NB-IoT protocol via MQTT.

## 🎯 What This Does

- Simulates **magnetic loop** and **ultrasonic** parking sensors
- Tracks vehicles entering/exiting parking spots in real-time
- Sends data via **MQTT** (simulates LoRaWAN gateway output)
- Event-based (car enter/exit) + periodic status updates
- Optional license plate recognition (ANPR cameras)

## 📁 Structure

```
parking-sensors/
├── parking_lots/
│   ├── lot_001_config.json    # Downtown parking (250 spots, ANPR enabled)
│   └── lot_002_config.json    # Train station P+R (180 spots, no ANPR)
├── parking_simulator.py       # Main simulator
├── setup_lorawan.sh           # MQTT broker setup
└── requirements.txt
```

## 🔧 Setup

### 1. Install MQTT Broker (LoRaWAN gateway)

```bash
chmod +x setup_lorawan.sh
./setup_lorawan.sh
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
paho-mqtt
```

## 🚀 Run Simulator

```bash
# Start simulator (runs all parking lots)
python parking_simulator.py
```

**In another terminal, monitor MQTT:**
```bash
mosquitto_sub -h localhost -t 'parking/#' -v
```

## 📡 Why LoRaWAN/MQTT?

| Feature | Why? |
|---------|------|
| **Long Range** | 2-15 km coverage (one gateway per district) |
| **Battery Life** | 5-10 years on single battery |
| **Low Cost** | $2-5 per sensor |
| **Low Bandwidth** | Perfect for parking (small, infrequent data) |

**Used by:** Amsterdam, Barcelona, Singapore for smart parking.

## 📊 Data Output

### 1. Event-Based (immediate when car enters/exits)

**Topic:** `parking/{lot_id}/event`

```json
{
  "device_type": "parking_iot_sensor",
  "protocol": "LoRaWAN",
  "parking_lot_id": "PARK_LUX_001",
  "timestamp": "2026-01-08T02:15:30",
  "event": {
    "event_type": "vehicle_entered",
    "spot_id": "SPOT_042",
    "vehicle_type": "sedan",
    "license_plate": "LUX-ABC-123"
  }
}
```

### 2. Periodic Status (every 30 seconds)

**Topic:** `parking/{lot_id}/status`

```json
{
  "parking_lot_id": "PARK_LUX_001",
  "timestamp": "2026-01-08T02:15:45",
  "occupancy": {
    "total_spots": 250,
    "occupied_spots": 187,
    "available_spots": 63,
    "occupancy_rate": 0.75,
    "status": "high"
  },
  "vehicle_breakdown": {
    "sedan": 120,
    "suv": 45,
    "electric": 22
  },
  "pricing": {
    "current_rate_per_hour": 3.44,
    "currency": "EUR"
  }
}
```

## 🎲 Simulation Features

### Time-Based Demand
- **9 AM - 6 PM** (business hours): 85% occupancy
- **6 PM - 10 PM** (evening): 60% occupancy
- **10 PM - 7 AM** (night): 20% occupancy

### Smart Features
- ✅ Vehicles enter/exit realistically
- ✅ Tracks parking duration (for billing)
- ✅ Dynamic pricing (based on occupancy)
- ✅ License plate recognition (optional)
- ✅ Battery monitoring (sensors report low battery)

### Logic Guarantees
- Car can **only exit if it entered first**
- Same license plate enters and exits
- Parking duration calculated correctly
- Spots freed after exit

## 🏙️ Parking Lots

| ID | Location | Type | Spots | ANPR | Protocol |
|----|----------|------|-------|------|----------|
| PARK_LUX_001 | Centre Ville (Downtown) | Underground | 250 | ✅ Yes | LoRaWAN |
| PARK_LUX_002 | Gare Centrale (Train Station) | Park & Ride | 180 | ❌ No | NB-IoT |

## 🔧 Configuration

**Config format (JSON):**
```json
{
  "parking_lot_id": "PARK_LUX_001",
  "parking_lot_name": "Centre Ville Parking",
  "total_spots": 250,
  "sensor_type": "magnetic_loop",
  "protocol": "LoRaWAN",
  "base_rate": 2.5,
  "has_license_plate_recognition": true,
  "location": {
    "gps": {"latitude": 49.6106, "longitude": 6.1312},
    "city": "Luxembourg City",
    "zone": "downtown"
  }
}
```

## ⚙️ How setup_lorawan.sh Works

```bash
# Installs Mosquitto MQTT Broker (simulates LoRaWAN gateway)
sudo apt install mosquitto mosquitto-clients

# Starts broker on port 1883
sudo systemctl start mosquitto
```

**MQTT = LoRaWAN Gateway Output**  
In real systems: LoRa sensors → Gateway → MQTT → Your pipeline

## 🧪 Testing

```bash
# Terminal 1: Start simulator
python parking_simulator.py

# Terminal 2: Monitor all parking data
mosquitto_sub -h localhost -t 'parking/#'

# Terminal 3: Monitor specific lot
mosquitto_sub -h localhost -t 'parking/PARK_LUX_001/#'

# Terminal 4: Monitor only events
mosquitto_sub -h localhost -t 'parking/+/event'
```

## 🛑 Stop Simulator

Press **Ctrl+C** to stop all parking lots gracefully.