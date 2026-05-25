import cv2
from ultralytics import YOLO
import logging
import numpy as np

# Thanks to Gemini
# 1. Shut YOLO up and turn off the fullscreen yellow "Video stream" warnings
logging.getLogger("ultralytics").setLevel(logging.ERROR)

# 2. Load pose estimation model
# yolov8n-pose Download from https://github.com/ultralytics/ultralytics/issues/1915
model = YOLO("yolov8n-pose.pt")

# 3. Camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam!")
    exit()

print("Webcam opened successfully! Press 'Q' on your keyboard to exit.")

while True:
    # 4.Capture frames from the webcam
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame from camera.")
        break

    # 5. Run inference (Note: verbose=False stops it from flooding the terminal 
    # with detection logs in real-time video)
    results = model(frame, verbose=False) 

    # 6. Process detection results
    for result in results:
        if result.boxes is None or len(result.boxes) == 0:
            continue
            
        # Loop through each detected person
        for i in range(len(result.boxes)):
            box = result.boxes.xyxy[i].cpu().numpy()
            x1, y1, x2, y2 = map(int, box)
            
            box_width = x2 - x1
            box_height = y2 - y1
            if box_height == 0: 
                continue
                
            aspect_ratio = box_width / box_height

            # --- Core Pose Logic: Calculating Torso Tilt Angle ---
            keypoints = result.keypoints.xy[i].cpu().numpy()
            
            # YOLOv8 keypoint indices: 5 and 6 are shoulders; 11 and 12 are hips.
            # We determine if a person is lying down by calculating the slope of the line 
            # connecting the mid-shoulder point and mid-hip point.
            try:
                if len(keypoints) > 12:
                    # Ensure keypoints are detected (coordinates are non-zero)
                    if keypoints[5][1] > 0 and keypoints[6][1] > 0 and keypoints[11][1] > 0 and keypoints[12][1] > 0:
                        # Calculate mid-shoulder point
                        shoulder_x = (keypoints[5][0] + keypoints[6][0]) / 2
                        shoulder_y = (keypoints[5][1] + keypoints[6][1]) / 2
                        
                        # Calculate mid-hip point
                        hip_x = (keypoints[11][0] + keypoints[12][0]) / 2
                        hip_y = (keypoints[11][1] + keypoints[12][1]) / 2
                        
                        # Calculate torso vector
                        dx = shoulder_x - hip_x
                        dy = shoulder_y - hip_y
                        
                        # Calculate angle with the horizontal line (in degrees)
                        angle = np.abs(np.degrees(np.arctan2(dy, dx)))
                        
                        # For debugging: draw the torso centerline on the body
                        cv2.line(frame, (int(shoulder_x), int(shoulder_y)), (int(hip_x), int(hip_y)), (255, 255, 0), 2)
                    else:
                        angle = 90  # Default to standing (90 degrees) if keypoints are not detected
                else:
                    angle = 90
            except:
                angle = 90

            # 7. [Upgraded Multi-Criteria Strategy]
            # Condition 1: Aspect ratio > 1.7 (Old strategy; if the bounding box is much wider than it is tall, they are likely lying down)
            # Condition 2: Torso angle < 35 degrees (Body is horizontal; since torso remains vertical when squatting or sitting, this avoids false positives)
            if aspect_ratio > 1.7 or angle < 35:
                # Fallen state
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                cv2.putText(frame, f"FALLEN! Angle: {int(angle)}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            else:
                # Normal state
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"Normal. Angle: {int(angle)}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # 8. Display the annotated real-time frame in a window (Must be inside the while loop)
    cv2.imshow("Robot Real-Time Vision", frame)

    # 9. Wait for 1 ms per frame; if 'q' is pressed on the keyboard, exit the loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 10. Release camera resources and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()