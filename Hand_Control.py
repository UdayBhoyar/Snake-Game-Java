import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Get screen size
screen_width, screen_height = pyautogui.size()
cap = cv2.VideoCapture(0)

# Store previous hand position and direction
prev_x, prev_y = None, None
current_direction = None
last_key_press_time = 0
key_cooldown = 0.2  # Reduced cooldown for more responsive controls

# Smoothing factor for hand movement
smoothing_factor = 0.3  # Reduced for more responsive movement

# Direction threshold - reduced for more sensitive detection
direction_threshold = 10  # Smaller threshold to detect minor movements

# Create a shorter gesture history for quicker direction changes
direction_history = []
history_size = 2  # Reduced history size for faster response

# Function to get the most common direction in history
def get_consistent_direction(history):
    if len(history) < history_size:
        return None
    
    # Check if the last N movements are the same
    if all(d == history[-1] for d in history[-history_size:]):
        return history[-1]
    return None

# Base position calibration
base_x, base_y = None, None
calibration_frames = 0
calibration_needed = 30  # Number of frames to use for calibration

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break
    
    # Flip the frame horizontally for a mirror effect
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    
    # Convert to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)
    
    # Create overlay for visual feedback
    overlay = frame.copy()
    
    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Using index finger tip for more precise control
            index_finger_tip = hand_landmarks.landmark[8]
            hand_x = int(index_finger_tip.x * w)
            hand_y = int(index_finger_tip.y * h)
            
            # Draw a circle at the control point for visual feedback
            cv2.circle(overlay, (hand_x, hand_y), 10, (0, 255, 0), -1)
            
            # Calibrate base position
            if base_x is None or calibration_frames < calibration_needed:
                if base_x is None:
                    base_x, base_y = hand_x, hand_y
                else:
                    # Average with existing base position for stability
                    base_x = (base_x * calibration_frames + hand_x) // (calibration_frames + 1)
                    base_y = (base_y * calibration_frames + hand_y) // (calibration_frames + 1)
                calibration_frames += 1
                cv2.putText(overlay, f"Calibrating: {calibration_frames}/{calibration_needed}", 
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                # Draw base position
                cv2.circle(overlay, (base_x, base_y), 15, (255, 0, 255), 2)
            else:
                # Draw base position
                cv2.circle(overlay, (base_x, base_y), 15, (255, 0, 255), 2)
                
                # Draw line from base to current position
                cv2.line(overlay, (base_x, base_y), (hand_x, hand_y), (255, 255, 0), 2)
                
                # Calculate displacement from base position
                dx = hand_x - base_x
                dy = hand_y - base_y
                
                # Determine the primary direction of movement relative to base
                direction = None
                if abs(dx) > abs(dy) and abs(dx) > direction_threshold:
                    direction = "right" if dx > 0 else "left"
                elif abs(dy) > abs(dx) and abs(dy) > direction_threshold:
                    direction = "down" if dy > 0 else "up"
                
                # Add to direction history
                if direction:
                    direction_history.append(direction)
                    if len(direction_history) > history_size * 2:
                        direction_history.pop(0)
                
                # Get consistent direction
                consistent_direction = get_consistent_direction(direction_history)
                
                # Only trigger movement if direction is consistent and different from current direction
                current_time = time.time()
                if (consistent_direction and 
                    (consistent_direction != current_direction or 
                     current_time - last_key_press_time > 0.5) and  # Allow repeating the same direction after 0.5s
                    current_time - last_key_press_time > key_cooldown):
                    
                    # Update current direction and press key
                    current_direction = consistent_direction
                    pyautogui.press(current_direction)
                    last_key_press_time = current_time
                    
                    # Visual feedback for direction change
                    feedback_color = {
                        "up": (0, 255, 0),    # Green
                        "down": (0, 0, 255),  # Red
                        "left": (255, 0, 0),  # Blue
                        "right": (255, 255, 0) # Cyan
                    }
                    
                    # Create direction indicator
                    cv2.putText(overlay, f"Direction: {current_direction}", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, 
                              feedback_color.get(current_direction, (255, 255, 255)), 2)
                
                # Display displacement values
                displacement_text = f"dx: {dx}, dy: {dy}"
                cv2.putText(frame, displacement_text, (10, h - 50), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # Update previous hand position for next frame
            prev_x, prev_y = hand_x, hand_y
    else:
        # If hand is lost, display warning
        cv2.putText(frame, "No hand detected", (w//2 - 100, h//2), 
                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # Add transparency to the overlay for visual feedback
    alpha = 0.7
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    
    # Display current direction
    if current_direction:
        cv2.putText(frame, f"Current: {current_direction}", 
                  (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Display threshold
    cv2.putText(frame, f"Threshold: {direction_threshold}", 
              (w - 180, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    cv2.imshow("Snake Game Hand Control", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('+') or key == ord('='):
        # Increase sensitivity (lower threshold)
        direction_threshold = max(5, direction_threshold - 1)
    elif key == ord('-'):
        # Decrease sensitivity (higher threshold)
        direction_threshold += 1
    elif key == ord('r'):
        # Reset calibration
        base_x, base_y = None, None
        calibration_frames = 0

cap.release()
cv2.destroyAllWindows()