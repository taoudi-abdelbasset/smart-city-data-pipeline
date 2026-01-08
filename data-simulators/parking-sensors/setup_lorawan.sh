#!/bin/bash
###############################################################################
# LoRaWAN Setup - Simple Installation
# Installs Mosquitto MQTT Broker (simulates LoRaWAN gateway)
###############################################################################

echo "=========================================================================="
echo "🔧 Installing LoRaWAN IoT Stack (MQTT Broker)"
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
    echo "✅ LoRaWAN IoT Stack READY!"
    echo "=========================================================================="
    echo ""
    echo "📡 MQTT Broker (simulates LoRaWAN gateway):"
    echo "   Host: localhost"
    echo "   Port: 1883"
    echo "   Status: RUNNING"
    echo ""
    echo "🧪 Test MQTT:"
    echo "   Subscribe: mosquitto_sub -h localhost -t 'parking/#'"
    echo "   Publish: mosquitto_pub -h localhost -t 'parking/test' -m 'Hello'"
    echo ""
    echo "🚀 Run parking simulator:"
    echo "   python parking_simulator.py"
    echo ""
else
    echo "❌ Failed to start MQTT Broker"
    exit 1
fi