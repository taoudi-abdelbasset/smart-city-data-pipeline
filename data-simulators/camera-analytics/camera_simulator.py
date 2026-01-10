#!/usr/bin/env python3
"""
Smart City - ROCK-SOLID RTSP Camera Server
This version includes ALL stability fixes:
- Auto-restart on crash
- Better FFmpeg parameters
- Health monitoring
- Graceful error handling
"""
import multiprocessing
import subprocess
import signal
import sys
import json
import time
from datetime import datetime
from pathlib import Path
import os

class StableRTSPCamera:
    """
    Rock-solid RTSP camera simulator with auto-recovery
    """
    
    def __init__(self, camera_folder):
        self.camera_folder = Path(camera_folder)
        self.metadata = self._load_metadata()
        self.video_path = self.camera_folder / "video.mp4"
        self.camera_id = self.metadata['camera_id']
        
        # Validate
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video not found: {self.video_path}")
        
        # RTSP config
        self.port = 8554
        stream_num = int(self.camera_id.split('_')[-1])
        self.stream_path = f"stream{stream_num}"
        self.rtsp_url = f"rtsp://127.0.0.1:{self.port}/{self.stream_path}"
        
        self.ffmpeg_process = None
        self.restart_count = 0
        self.max_restarts = 10
        
        print(f"✅ Camera {self.camera_id} initialized")
        print(f"   Stream URL: {self.rtsp_url}")
        print(f"   Video: {self.video_path}")
    
    def _load_metadata(self):
        """Load camera metadata"""
        metadata_path = self.camera_folder / "metadata.json"
        with open(metadata_path, 'r') as f:
            return json.load(f)
    
    def _build_ffmpeg_command(self):
        """
        Build OPTIMIZED FFmpeg command for stable streaming
        Key fixes:
        - Lower bitrate to prevent network issues
        - Smaller GOP for faster recovery
        - TCP transport for reliability
        - Proper error handling flags
        """
        return [
            'ffmpeg',
            '-re',                          # Real-time
            '-stream_loop', '-1',           # Infinite loop
            '-i', str(self.video_path),     # Input
            
            # Video encoding (optimized for stability)
            '-c:v', 'libx264',
            '-preset', 'veryfast',          # Fast encoding
            '-tune', 'zerolatency',         # Low latency
            '-b:v', '1M',                   # Lower bitrate (1Mbps)
            '-maxrate', '1M',
            '-bufsize', '2M',
            '-g', '30',                     # Smaller GOP (1 sec at 30fps)
            '-sc_threshold', '0',
            
            # Frame rate control
            '-r', '30',                     # Fixed 30 FPS
            
            # No audio (reduces complexity)
            '-an',
            
            # RTSP output settings
            '-f', 'rtsp',
            '-rtsp_transport', 'tcp',       # TCP is more reliable than UDP
            
            # Error handling
            '-loglevel', 'warning',         # Only show warnings/errors
            '-nostats',                     # No progress stats
            
            # Output URL
            self.rtsp_url
        ]
    
    def _is_process_healthy(self):
        """Check if FFmpeg process is still running"""
        if self.ffmpeg_process is None:
            return False
        
        return self.ffmpeg_process.poll() is None
    
    def start_streaming(self):
        """
        Start FFmpeg streaming with auto-restart on failure
        """
        while self.restart_count < self.max_restarts:
            try:
                print(f"\n🎥 Starting stream: {self.camera_id} (attempt {self.restart_count + 1})")
                
                # Build command
                cmd = self._build_ffmpeg_command()
                
                # Start FFmpeg
                self.ffmpeg_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                # Wait for stream to start
                time.sleep(3)
                
                # Check if started successfully
                if self._is_process_healthy():
                    print(f"✅ Stream LIVE: {self.rtsp_url}")
                    
                    # Monitor stream health
                    self._monitor_stream()
                else:
                    # FFmpeg died immediately
                    stdout, stderr = self.ffmpeg_process.communicate()
                    print(f"❌ Stream failed to start:")
                    print(f"   Error: {stderr[-500:]}")
                    
                    self.restart_count += 1
                    
                    if self.restart_count < self.max_restarts:
                        print(f"   Retrying in 5 seconds...")
                        time.sleep(5)
                    
            except Exception as e:
                print(f"❌ Exception starting stream: {e}")
                self.restart_count += 1
                time.sleep(5)
        
        print(f"❌ Max restarts ({self.max_restarts}) reached for {self.camera_id}")
    
    def _monitor_stream(self):
        """
        Monitor stream and restart if it crashes
        """
        while self._is_process_healthy():
            time.sleep(10)  # Check every 10 seconds
        
        # Stream died
        print(f"⚠️  Stream died: {self.camera_id}")
        
        # Get error output
        if self.ffmpeg_process:
            try:
                stdout, stderr = self.ffmpeg_process.communicate(timeout=2)
                print(f"   FFmpeg error: {stderr[-200:]}")
            except:
                pass
        
        # Increment restart counter and retry
        self.restart_count += 1
        
        if self.restart_count < self.max_restarts:
            print(f"   Auto-restarting (attempt {self.restart_count + 1})...")
            time.sleep(2)
            self.start_streaming()
    
    def stop(self):
        """Stop streaming gracefully"""
        if self.ffmpeg_process and self._is_process_healthy():
            print(f"🛑 Stopping {self.camera_id}...")
            self.ffmpeg_process.terminate()
            
            try:
                self.ffmpeg_process.wait(timeout=5)
            except:
                self.ffmpeg_process.kill()
            
            print(f"✅ Stopped {self.camera_id}")


def run_camera_process(camera_folder):
    """
    Run camera in separate process with its own error handling
    """
    try:
        camera = StableRTSPCamera(camera_folder)
        camera.start_streaming()
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping camera: {camera_folder.name}")
        camera.stop()
    except Exception as e:
        print(f"❌ Camera process error: {e}")
        import traceback
        traceback.print_exc()


def check_mediamtx():
    """Check if MediaMTX is running"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'mediamtx'],
            capture_output=True
        )
        return result.returncode == 0
    except:
        return False


def main():
    """
    Main function - starts ALL cameras with stability features
    """
    print("===============================================================================")
    print("📹 ROCK-SOLID RTSP Camera Simulator")
    print("===============================================================================")
    print("")
    
    # Check if MediaMTX is running
    if not check_mediamtx():
        print("❌ MediaMTX is NOT running!")
        print("")
        print("Start MediaMTX first:")
        print("  Terminal 1: ./mediamtx")
        print("  Terminal 2: python3 camera_simulator_stable.py")
        print("")
        sys.exit(1)
    
    print("✅ MediaMTX is running")
    print("")
    
    # Find all cameras
    cameras_dir = Path("cameras")
    
    if not cameras_dir.exists():
        print("❌ 'cameras/' folder not found")
        sys.exit(1)
    
    camera_folders = [f for f in cameras_dir.iterdir() if f.is_dir()]
    
    if not camera_folders:
        print("❌ No cameras found")
        sys.exit(1)
    
    print(f"📹 Found {len(camera_folders)} cameras")
    print("="*80)
    print("")
    
    # Start each camera in separate process
    processes = []
    
    try:
        for folder in sorted(camera_folders):
            p = multiprocessing.Process(
                target=run_camera_process,
                args=(folder,)
            )
            p.start()
            processes.append(p)
            print(f"✅ Started process for {folder.name}")
            time.sleep(2)  # Stagger starts
        
        print("")
        print("="*80)
        print(f"✅ All {len(processes)} cameras started!")
        print("="*80)
        print("")
        print("📺 Test streams:")
        for i, folder in enumerate(sorted(camera_folders), 1):
            print(f"  vlc rtsp://localhost:8554/stream{i}")
        print("")
        print("Press Ctrl+C to stop all cameras")
        print("="*80)
        
        # Wait for all processes
        for p in processes:
            p.join()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all cameras...")
        for p in processes:
            p.terminate()
        
        # Wait for graceful shutdown
        time.sleep(2)
        
        # Force kill if needed
        for p in processes:
            if p.is_alive():
                p.kill()
        
        for p in processes:
            p.join()
        
        print("✅ All cameras stopped")
    
    except Exception as e:
        print(f"❌ Main process error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()