#!/usr/bin/env python3
"""
Smart City - REAL RTSP Camera Server
Creates ACTUAL RTSP server streaming video from files
Uses FFmpeg to create real RTSP stream that consumers can connect to
"""
import multiprocessing
import cv2
import json
import time
import subprocess
import signal
import sys
from datetime import datetime
from pathlib import Path
import threading

class RTSPCameraServer:
    """
    Creates REAL RTSP server for surveillance camera simulation
    Streams actual video via RTSP protocol on local network
    """
    
    def __init__(self, camera_folder):
        self.camera_folder = Path(camera_folder)
        self.metadata = self._load_metadata()
        self.video_path = self.camera_folder / "video.mp4"
        
        # Validate files exist
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video not found: {self.video_path}")
        
        # Parse RTSP URL
        self.rtsp_url = self.metadata['camera_specs']['rtsp_url']
        self.port = self._extract_port(self.rtsp_url)
        self.stream_path = self._extract_stream_path(self.rtsp_url)
        
        # Build actual RTSP URL (using localhost and corrected port)
        self.actual_rtsp_url = f"rtsp://127.0.0.1:{self.port}/{self.stream_path}"
        
        self.ffmpeg_process = None
        
        print(f"✅ RTSP Camera Server {self.metadata['camera_id']} initialized")
        print(f"   Original URL: {self.rtsp_url}")
        print(f"   Actual Stream URL: {self.actual_rtsp_url}")
        print(f"   Video: {self.video_path}")
        print(f"   Location: {self.metadata['location']['address']}")
        print(f"   GPS: ({self.metadata['location']['gps']['latitude']}, {self.metadata['location']['gps']['longitude']})")
    
    def _load_metadata(self):
        """Load camera metadata from JSON"""
        metadata_path = self.camera_folder / "metadata.json"
        with open(metadata_path, 'r') as f:
            return json.load(f)
    
    def _extract_port(self, rtsp_url):
        """Extract port from RTSP URL"""
        # rtsp://192.168.1.101:554/stream1
        # Port 554 requires root, use 8554 instead
        try:
            parts = rtsp_url.split(':')
            port = parts[2].split('/')[0]
            requested_port = int(port)
            # Use non-privileged port (8554 instead of 554)
            return 8554 if requested_port == 554 else requested_port
        except:
            return 8554  # Default RTSP port
    
    def _extract_stream_path(self, rtsp_url):
        """Extract stream path from RTSP URL"""
        # rtsp://192.168.1.101:554/stream1 -> stream1
        try:
            return rtsp_url.split('/')[-1]
        except:
            return 'stream'
    
    def start_rtsp_server(self):
        """
        Stream video to RTSP server using FFmpeg
        Requires MediaMTX or rtsp-simple-server running on localhost
        """
        
        print(f"\n🎥 Starting RTSP stream publisher...")
        print(f"   Publishing to: {self.actual_rtsp_url}")
        print(f"   Video looping: {self.video_path}")
        print(f"   Port: {self.port}")
        print(f"   ⚠️  Make sure MediaMTX/rtsp-simple-server is running!")
        
        # FFmpeg command to PUBLISH to RTSP server
        # Note: This requires MediaMTX or rtsp-simple-server running
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-re',                          # Real-time streaming
            '-stream_loop', '-1',           # Loop video infinitely
            '-i', str(self.video_path),     # Input video
            '-c:v', 'libx264',              # Re-encode to H.264
            '-preset', 'ultrafast',         # Fast encoding
            '-tune', 'zerolatency',         # Low latency
            '-b:v', '2M',                   # Bitrate 2Mbps (adjust for quality)
            '-maxrate', '2M',               # Max bitrate
            '-bufsize', '4M',               # Buffer size
            '-g', '60',                     # GOP size (2 seconds at 30fps)
            '-sc_threshold', '0',           # Disable scene change detection
            '-an',                          # No audio (reduces issues)
            '-f', 'rtsp',                   # RTSP output
            '-rtsp_transport', 'tcp',       # Use TCP for reliability
            self.actual_rtsp_url
        ]
        
        try:
            # Start FFmpeg process (publishes to RTSP server)
            # Keep stdout/stderr open to see errors
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Wait a moment for stream to start
            time.sleep(3)
            
            # Check if process is still running
            if self.ffmpeg_process.poll() is None:
                print(f"✅ RTSP stream publishing!")
                print(f"   Connect with: vlc {self.actual_rtsp_url}")
                print(f"   Or use: cv2.VideoCapture('{self.actual_rtsp_url}')")
                print(f"   FFmpeg PID: {self.ffmpeg_process.pid}")
                print(f"   Press Ctrl+C to stop\n")
                return True
            else:
                # FFmpeg died, show error
                stdout, stderr = self.ffmpeg_process.communicate()
                print(f"❌ FFmpeg failed!")
                print(f"\nFFmpeg Error Output:")
                print(stderr[-500:] if len(stderr) > 500 else stderr)  # Last 500 chars
                print(f"\n💡 Troubleshooting:")
                print(f"   1. Is MediaMTX running? (./mediamtx in another terminal)")
                print(f"   2. Check if video file is valid: ffprobe {self.video_path}")
                return False
            
        except FileNotFoundError:
            print("❌ FFmpeg not found! Install it:")
            print("   sudo apt install ffmpeg")
            return False
        except Exception as e:
            print(f"❌ Failed to start RTSP stream: {e}")
            return False
    
    def send_metadata(self, interval_seconds=5):
        """
        Send camera metadata periodically
        This runs alongside RTSP stream
        """
        print(f"📡 Sending camera metadata every {interval_seconds} seconds...")
        
        try:
            while True:
                metadata_packet = {
                    "device_type": "rtsp_camera",
                    "camera_id": self.metadata['camera_id'],
                    "camera_name": self.metadata['camera_name'],
                    "rtsp_url": self.rtsp_url,
                    "timestamp": datetime.now().isoformat(),
                    "location": self.metadata['location'],
                    "stream_info": {
                        "resolution": self.metadata['camera_specs']['resolution'],
                        "fps": self.metadata['camera_specs']['fps'],
                        "encoding": self.metadata['camera_specs']['encoding']
                    },
                    "camera_status": {
                        "online": True,
                        "streaming": True,
                        "connection_quality": "excellent"
                    }
                }
                
                # Output metadata (consumer can collect this)
                print(json.dumps(metadata_packet, indent=2))
                print("-" * 80)
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            pass
    
    def stop(self):
        """Stop RTSP server"""
        if self.ffmpeg_process:
            print(f"\n🛑 Stopping RTSP server {self.metadata['camera_id']}...")
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
            print("✅ Server stopped")
    
    def run(self):
        """
        Run RTSP server with metadata output
        Two threads:
        1. FFmpeg RTSP stream (video)
        2. Metadata output (JSON)
        """
        
        # Start RTSP server
        if not self.start_rtsp_server():
            return
        
        # Wait a bit for server to start
        time.sleep(2)
        
        # Send metadata in main thread
        try:
            self.send_metadata(interval_seconds=5)
        except KeyboardInterrupt:
            self.stop()


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\n\n🛑 Shutting down all RTSP servers...')
    sys.exit(0)


def main():
    """
    Main function - starts REAL RTSP servers for all cameras
    """
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get all camera folders
    cameras_dir = Path("cameras")
    
    if not cameras_dir.exists():
        print("❌ Error: 'cameras/' folder not found")
        print("   Create: cameras/camera_001/ with video.mp4 and metadata.json")
        sys.exit(1)
    
    camera_folders = [f for f in cameras_dir.iterdir() if f.is_dir()]
    
    if not camera_folders:
        print("❌ Error: No cameras found in cameras/ folder")
        sys.exit(1)
    
    print(f"📡 Found {len(camera_folders)} cameras")
    print("="*80)
    
    # Initialize all cameras
    cameras = []
    for folder in sorted(camera_folders):
        try:
            cam = RTSPCameraServer(folder)
            cameras.append(cam)
        except Exception as e:
            print(f"❌ Failed to load {folder.name}: {e}")
    
    if not cameras:
        print("❌ No cameras could be initialized")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("🚀 Starting REAL RTSP servers...")
    print("   Each camera creates actual RTSP stream")
    print("   Consumers can connect via RTSP protocol")
    print("   Metadata is sent to stdout (pipe to Kafka)")
    print("="*80 + "\n")
    
    # For demo: start first camera
    # In production: start all cameras in separate processes
    # cameras[0].run()
    processes = []
    for camera in cameras:
        p = multiprocessing.Process(target=camera.run)
        p.start()
        processes.append(p)

    # Wait for all processes
    for p in processes:
        p.join()


if __name__ == "__main__":
    main()