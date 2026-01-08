#!/bin/bash
###############################################################################
# MQTT Broker Setup
# Used by: Parking sensors, Air Quality sensors, Weather stations
###############################################################################
echo "=========================================================================="
echo "🔧 Installing MQTT Broker (IoT Communication)"
echo "=========================================================================="
echo ""

# Install Mosquitto MQTT Broker
echo "📦 Installing Mosquitto MQTT Broker..."
sudo apt update
sudo apt install -y mosquitto mosquitto-clients

# Start Mosquitto service
echo "🚀 Starting MQTT Broker..."
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Check status
if systemctl is-active --quiet mosquitto; then
    echo ""
    echo "=========================================================================="
    echo "✅ MQTT Broker READY!"
    echo "=========================================================================="
    echo ""
    echo "📡 MQTT Broker:"
    echo "   Host: localhost"
    echo "   Port: 1883"
    echo "   Status: RUNNING"
    echo ""
    echo "🧪 Test MQTT:"
    echo "   Subscribe all: mosquitto_sub -h localhost -t '#' -v"
    echo "   Parking: mosquitto_sub -h localhost -t 'parking/#'"
    echo "   Air Quality: mosquitto_sub -h localhost -t 'air_quality/#'"
    echo ""
    echo "🚀 Run simulators:"
    echo "   python parking_simulator.py"
    echo "   python air_quality_simulator.py"
    echo ""
else
    echo "❌ Failed to start MQTT Broker"
    exit 1
fi