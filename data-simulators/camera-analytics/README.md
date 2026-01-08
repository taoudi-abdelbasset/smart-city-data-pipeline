# 📷 RTSP Camera Surveillance Simulator

Simulates real RTSP surveillance cameras for Smart City IoT testing.

## 🎯 What This Does

- Creates **REAL RTSP streams** from video files
- Each camera streams H.264 video via RTSP protocol
- Outputs camera metadata as JSON (location, status, etc.)
- Simulates multiple surveillance cameras simultaneously

## 📁 Structure

```
camera-analytics/
├── cameras/
│   ├── camera_001/          # Traffic camera (downtown)
│   │   ├── video.mp4        # Traffic video
│   │   └── metadata.json    # GPS, location, specs
│   └── camera_002/          # Pedestrian camera (train station)
│       ├── video.mp4        # Pedestrian video
│       └── metadata.json
├── camera_simulator.py      # Main RTSP server
├── mediamtx                 # RTSP server binary
└── requirements.txt
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Setup RTSP Server

```bash
# Download MediaMTX (one-time setup)
./setup_rtsp.sh
```

### 3. Run Cameras

**Terminal 1** - Start RTSP server:
```bash
./mediamtx
```

**Terminal 2** - Run camera simulator:
```bash
python camera_simulator.py
```

**Terminal 3** - Watch stream:
```bash
# Camera 1 (traffic)
ffplay rtsp://127.0.0.1:8554/stream1

# Camera 2 (pedestrian)
ffplay rtsp://127.0.0.1:8554/stream2
```

## 🔌 Connect from Consumer

```python
import cv2

# Connect to RTSP stream
cap = cv2.VideoCapture('rtsp://127.0.0.1:8554/stream1')

while True:
    ret, frame = cap.read()
    if ret:
        # Process frame (YOLO detection, analytics, etc.)
        cv2.imshow('Camera', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
```

## 📡 Data Output

The simulator outputs TWO things:

### 1. RTSP Video Stream
- **Protocol:** RTSP (Real-Time Streaming Protocol)
- **URL:** `rtsp://127.0.0.1:8554/stream1` (camera 1)
- **URL:** `rtsp://127.0.0.1:8554/stream2` (camera 2)
- **Encoding:** H.264 video
- **Consumer:** Your data pipeline connects here for video analytics

### 2. Metadata JSON (stdout)
```json
{
  "device_type": "rtsp_camera",
  "camera_id": "CAM_LUX_001",
  "rtsp_url": "rtsp://127.0.0.1:8554/stream1",
  "timestamp": "2026-01-08T01:30:00",
  "location": {
    "gps": {"latitude": 49.6116, "longitude": 6.1319},
    "city": "Luxembourg City",
    "zone": "downtown"
  },
  "camera_status": {
    "online": true,
    "streaming": true
  }
}
```

## 🎥 Camera Details

| Camera | Type | Location | Stream URL |
|--------|------|----------|------------|
| CAM_LUX_001 | Traffic | Boulevard Royal (Downtown) | `rtsp://127.0.0.1:8554/stream1` |
| CAM_LUX_002 | Pedestrian | Gare Centrale (Train Station) | `rtsp://127.0.0.1:8554/stream2` |

## 🔧 Adding More Cameras

1. Create new folder: `cameras/camera_003/`
2. Add `video.mp4` and `metadata.json`
3. Change `rtsp_url` to unique stream path (e.g., `stream3`)
4. Run simulator - auto-detects all cameras

## ⚠️ Troubleshooting

**Stream not working?**
- Check MediaMTX is running: `./mediamtx`
- Verify unique stream paths in metadata.json
- Test with: `ffplay rtsp://127.0.0.1:8554/stream1`

**Video laggy/packet loss?**
- Script re-encodes video automatically
- Check video file is valid: `ffprobe cameras/camera_001/video.mp4`

**Can't connect?**
- Port 8554 is default (non-privileged)
- Check firewall: `sudo ufw allow 8554`

## 📦 Requirements

- Python 3.8+
- OpenCV (`opencv-python`)
- FFmpeg (system package)
- MediaMTX (included, binary)