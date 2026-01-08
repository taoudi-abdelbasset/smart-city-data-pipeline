#!/bin/bash
echo "Setting up RTSP server (MediaMTX)..."

# Download MediaMTX
wget https://github.com/bluenviron/mediamtx/releases/download/v1.9.3/mediamtx_v1.9.3_linux_amd64.tar.gz
tar -xzf mediamtx_v1.9.3_linux_amd64.tar.gz
rm mediamtx_v1.9.3_linux_amd64.tar.gz

echo "✅ MediaMTX downloaded!"
echo ""
echo "To run:"
echo "  Terminal 1: ./mediamtx"
echo "  Terminal 2: python camera_simulator.py"