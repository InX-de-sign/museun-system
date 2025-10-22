import cv2
from ultralytics import YOLO

# IMPORTANT: Update this path to YOUR model location
model = YOLO("cv\models\\best_detect_3D.onnx")

# Try different camera indices (0, 1, 2)
cap = cv2.VideoCapture(0)  # Try 0 first, then 1, then 2

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# Settings
imgsz = 640
conf = 0.80 

print(f"Model classes: {model.names}")
print(f"Camera opened successfully!")
print("Press 'q' to quit\n")

frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")
        break
    
    frame_count += 1
    
    # Perform detection
    results = model.predict(source=frame, imgsz=imgsz, conf=conf, device="cpu", verbose=False)
    
    # Print detections every 30 frames
    if frame_count % 30 == 0:
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            print(f"\n✅ Frame {frame_count}: {len(results[0].boxes)} detections!")
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = model.names[cls_id]
                print(f"   - {class_name}: {confidence:.2%}")
        else:
            print(f"❌ Frame {frame_count}: No detections")
    
    # Draw annotations
    annotated_frame = results[0].plot()
    
    # Display
    cv2.imshow("Artwork Recognition Test", annotated_frame)
    
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print(f"\nTotal frames processed: {frame_count}")