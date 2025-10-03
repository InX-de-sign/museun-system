import cv2
from ultralytics import YOLO
import httpx
import asyncio

model = YOLO("F:/_VScode2/museun_system/inference/models/best_detect.onnx")

# Connect to MediaMTX stream (same stream Docker is watching)
cap = cv2.VideoCapture("rtsp://localhost:8554/cam1")

async def send_to_chatbot(label, confidence):
    """Send detection to chatbot like the real inference does"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8000/cv/detection",
                json={"label": label, "confidence": confidence, "user_id": "default_user"}
            )
            print(f"Sent to chatbot: {label}")
    except Exception as e:
        print(f"Failed to send: {e}")

print("Viewing stream from MediaMTX - Press 'q' to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Lost stream")
        break
    
    # Run detection (same as Docker is doing)
    results = model(frame, conf=0.5)
    annotated = results[0].plot()
    
    # If something detected, send to chatbot
    for box in results[0].boxes:
        label = model.names[int(box.cls)]
        confidence = float(box.conf)
        print(f"Detected: {label} ({confidence:.2f})")
        # Uncomment to send:
        # asyncio.run(send_to_chatbot(label, confidence))
    
    cv2.imshow("Detection View", annotated)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()