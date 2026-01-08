#!/bin/bash
###############################################################################
# SUMO TraCI Setup Script
# Sets up Python environment for SUMO TraCI connection
###############################################################################

echo "=========================================================================="
echo "🚗 Setting up SUMO TraCI for Traffic Data Collection"
echo "=========================================================================="
echo ""

# Check if SUMO is installed
if ! command -v sumo &> /dev/null; then
    echo "❌ SUMO not found! Installing SUMO..."
    echo ""
    
    # Add SUMO repository
    sudo add-apt-repository ppa:sumo/stable
    sudo apt update
    sudo apt install -y sumo sumo-tools sumo-doc
    
    echo "✅ SUMO installed!"
else
    echo "✅ SUMO found: $(sumo --version | head -n 1)"
fi

echo ""

# Set SUMO_HOME environment variable
if [ -z "$SUMO_HOME" ]; then
    echo "📝 Setting SUMO_HOME environment variable..."
    
    # Find SUMO installation
    SUMO_PATH=$(which sumo)
    SUMO_DIR=$(dirname $(dirname $SUMO_PATH))
    
    # Add to bashrc
    echo "export SUMO_HOME=$SUMO_DIR" >> ~/.bashrc
    export SUMO_HOME=$SUMO_DIR
    
    echo "✅ SUMO_HOME set to: $SUMO_HOME"
else
    echo "✅ SUMO_HOME already set: $SUMO_HOME"
fi

echo ""
echo "=========================================================================="
echo "✅ SUMO TraCI Setup Complete!"
echo "=========================================================================="
echo ""
echo "📍 Your LuST scenario location:"
echo "   ~/Downloads/firefox-install/BigData/simulators/LuST/LuSTScenario"
echo ""
echo "🚀 To run LuST with TraCI:"
echo "   cd ~/Downloads/firefox-install/BigData/simulators/LuST/LuSTScenario/scenario"
echo "   sumo-gui -c dua.actuated.sumocfg --remote-port 8813"
echo ""
echo "   OR headless (no GUI):"
echo "   sumo -c dua.actuated.sumocfg --remote-port 8813"
echo ""
echo "📡 Then run MQTT connector:"
echo "   python sumo_mqtt_connector.py"
echo ""