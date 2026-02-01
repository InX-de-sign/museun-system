import cv2
import subprocess
import time

# Open your webcam (same index that worked in PC_artwork_recognition.py, which is 0)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot open camera 0, trying camera 1...")
    cap = cv2.VideoCapture(1)

# Get camera properties
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

print(f"Camera: {width}x{height} @ {fps}fps")
print("Streaming to MediaMTX at rtsp://localhost:8554/cam0")
print("Press Ctrl+C to stop")

# FFmpeg command to stream to MediaMTX
ffmpeg_cmd = [
    'ffmpeg',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', f'{width}x{height}',
    '-r', str(fps),
    '-i', '-',
    '-c:v', 'libx264',
    '-preset', 'ultrafast',
    '-tune', 'zerolatency',
    '-f', 'rtsp',
    '-rtsp_transport', 'tcp',
    'rtsp://localhost:8554/cam1'
]

process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, 
                          stderr=subprocess.DEVNULL)

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        # Write frame to ffmpeg
        process.stdin.write(frame.tobytes())
        
except KeyboardInterrupt:
    print("\nStopping stream...")
finally:
    cap.release()
    process.stdin.close()
    process.wait()
    print("Stream stopped")