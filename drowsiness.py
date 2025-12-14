import cv2
import numpy as np
from scipy.spatial import distance
import time
import winsound  # For alarm beep sound

def eye_aspect_ratio(eye):
    """Calculate the Eye Aspect Ratio (EAR)"""
    # Compute euclidean distances between vertical eye landmarks
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    
    # Compute euclidean distance between horizontal eye landmarks
    C = distance.euclidean(eye[0], eye[3])
    
    # Calculate EAR
    ear = (A + B) / (2.0 * C)
    return ear

# Constants - ADJUST THESE VALUES
EAR_THRESHOLD = 0.25  # Eye Aspect Ratio threshold
CONSEC_FRAMES = 70    # Number of consecutive frames (increase = less sensitive, decrease = more sensitive)
                      # 20 frames = ~0.7 seconds at 30fps
                      # 40 frames = ~1.3 seconds at 30fps
                      # 60 frames = ~2 seconds at 30fps
                      # 70 frames = ~2.3 seconds at 30fps

# Initialize counters
frame_counter = 0
drowsy_alert = False

# Load Haar Cascade classifiers
print("Loading face and eye detectors...")
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# Start video capture
print("Starting video capture...")
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Variables for eye blink detection
eyes_closed_frames = 0
total_blinks = 0
last_eye_state = "open"
blink_in_progress = False
max_blink_frames = 10  # Maximum frames for a valid blink (~0.3 seconds)

# Smoothing variables to reduce flickering
eye_status_history = []
history_length = 5  # Number of frames to consider for smoothing

print("System initialized. Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break
    
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(100, 100))
    
    eyes_detected = False
    
    for (x, y, w, h) in faces:
        # Draw rectangle around face
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        # Region of interest for eyes (upper half of face)
        roi_gray = gray[y:y+int(h*0.6), x:x+w]
        roi_color = frame[y:y+int(h*0.6), x:x+w]
        
        # Detect eyes
        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=10, minSize=(20, 20))
        
        # Draw rectangles around eyes
        for (ex, ey, ew, eh) in eyes:
            cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)
            eyes_detected = True
        
        # Add current detection to history
        eye_status_history.append(len(eyes))
        if len(eye_status_history) > history_length:
            eye_status_history.pop(0)
        
        # Use average of history to smooth detection
        avg_eyes = sum(eye_status_history) / len(eye_status_history)
        eyes_stable = avg_eyes >= 1.5  # Consider eyes open if average >= 1.5
        
        # Check if both eyes are detected (using smoothed detection)
        if eyes_stable:
            # Eyes are open and detected
            if last_eye_state == "closed" and blink_in_progress and eyes_closed_frames <= max_blink_frames:
                # Valid blink completed (closed briefly then opened)
                total_blinks += 1
                blink_in_progress = False
            
            eyes_closed_frames = 0
            current_eye_state = "open"
            
            # Reset drowsiness if eyes are open
            if drowsy_alert:
                drowsy_alert = False
                frame_counter = 0
        
        # If eyes not detected (possibly closed)
        else:
            eyes_closed_frames += 1
            current_eye_state = "closed"
            
            # Start tracking a potential blink
            if last_eye_state == "open" and not blink_in_progress:
                blink_in_progress = True
            
            # If closed too long, it's not a blink - it's drowsiness
            if eyes_closed_frames > max_blink_frames:
                blink_in_progress = False
            
            # Check for drowsiness
            if eyes_closed_frames >= CONSEC_FRAMES:
                if not drowsy_alert:
                    drowsy_alert = True
                    # Play alarm beep
                    winsound.Beep(2500, 1000)  # 2500Hz frequency, 1000ms duration
                
                cv2.putText(frame, "DROWSINESS ALERT!", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
                cv2.putText(frame, "WAKE UP!", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
        
        last_eye_state = current_eye_state
        
        # Display eye status (smoothed)
        status_color = (0, 255, 0) if eyes_stable else (0, 165, 255)
        eye_status = "Eyes Open" if eyes_stable else "Eyes Closed/Not Detected"
        cv2.putText(frame, eye_status, (10, frame.shape[0] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
    
    # Display statistics with magenta color for visibility
    cv2.putText(frame, f"Closed Frames: {eyes_closed_frames}", (10, 110),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)  # Magenta text
    
    cv2.putText(frame, f"Total Blinks: {total_blinks}", (10, 140),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)  # Magenta text
    
    # Show if no face detected
    if len(faces) == 0:
        cv2.putText(frame, "No face detected", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    
    # Display the frame
    cv2.imshow("Driver Drowsiness Detection - OpenCV", frame)
    
    # Exit on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
print("Shutting down...")
cap.release()
cv2.destroyAllWindows()