import cv2
import mediapipe as mp
import time
import math

print("Starting drowsiness detection...")

# --- Configuration ---
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# --- Drowsiness Detection Config ---
EAR_THRESHOLD = 0.20  # Threshold for triggering "drowsy"
EAR_CONSEC_FRAMES = 3  # Number of consecutive frames eye must be closed
COUNTER = 0 # Frame counter for consecutive closed eyes

# --- MediaPipe Initialization ---
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Specific landmarks for the eyes
# See: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/face_model_landmarks.pbtxt
# These are the 6 landmarks for each eye
LANDMARKS_LEFT_EYE = [362, 385, 387, 263, 373, 380]
LANDMARKS_RIGHT_EYE = [33, 160, 158, 133, 153, 144]

def euclidean_dist(p1, p2):
    """Helper function to calculate distance between two (x, y) points"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def calculate_ear(landmarks, eye_indices, frame_shape):
    """Calculates the Eye Aspect Ratio (EAR) for one eye.
    
    Args:
        landmarks: The full list of 478 landmarks from MediaPipe
        eye_indices: The 6 specific landmark indices for the eye
        frame_shape: The (height, width) of the video frame
    """
    try:
        # Get (x, y) coordinates for the 6 eye landmarks
        # We multiply by frame dimensions to get pixel coordinates
        p1 = (landmarks[eye_indices[0]].x * frame_shape[1], landmarks[eye_indices[0]].y * frame_shape[0])
        p2 = (landmarks[eye_indices[1]].x * frame_shape[1], landmarks[eye_indices[1]].y * frame_shape[0])
        p3 = (landmarks[eye_indices[2]].x * frame_shape[1], landmarks[eye_indices[2]].y * frame_shape[0])
        p4 = (landmarks[eye_indices[3]].x * frame_shape[1], landmarks[eye_indices[3]].y * frame_shape[0])
        p5 = (landmarks[eye_indices[4]].x * frame_shape[1], landmarks[eye_indices[4]].y * frame_shape[0])
        p6 = (landmarks[eye_indices[5]].x * frame_shape[1], landmarks[eye_indices[5]].y * frame_shape[0])

        # --- Calculate EAR ---
        # Vertical distances
        vert_dist1 = euclidean_dist(p2, p6)
        vert_dist2 = euclidean_dist(p3, p5)
        # Horizontal distance
        horiz_dist = euclidean_dist(p1, p4)

        # Eye Aspect Ratio
        ear = (vert_dist1 + vert_dist2) / (2.0 * horiz_dist)
        return ear
    except Exception as e:
        print(f"Error calculating EAR: {e}")
        return 0.0

# --- Main Application ---
try:
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: Could not open camera at index {CAMERA_INDEX}.")
        exit()

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    print("Camera opened. Press 'q' to quit.")

    # Use FaceMesh model
    with mp_face_mesh.FaceMesh(
        max_num_faces=1,  # We only care about one user
        refine_landmarks=True, # This gives us the detailed iris/eye landmarks
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as face_mesh:

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Can't receive frame.")
                break
            
            # Get frame shape
            ih, iw, _ = frame.shape

            # --- Face Mesh Logic ---
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(frame_rgb)
            
            ear_avg = 0.0 # Default value
            
            if results.multi_face_landmarks:
                # We found a face. We only use the first one.
                face_landmarks = results.multi_face_landmarks[0].landmark
                
                # --- EAR Calculation ---
                ear_left = calculate_ear(face_landmarks, LANDMARKS_LEFT_EYE, (ih, iw))
                ear_right = calculate_ear(face_landmarks, LANDMARKS_RIGHT_EYE, (ih, iw))
                
                # Average the EAR for stability
                ear_avg = (ear_left + ear_right) / 2.0
                
                # --- Drowsiness Logic ---
                if ear_avg < EAR_THRESHOLD:
                    COUNTER += 1
                    if COUNTER >= EAR_CONSEC_FRAMES:
                        # Display DROWSY warning
                        cv2.putText(frame, "DROWSY", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                else:
                    COUNTER = 0 # Reset counter if eyes are open

                # Display the EAR value on the frame
                cv2.putText(frame, f"EAR: {ear_avg:.2f}", (480, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                # Optional: Draw the eye landmarks (can be slow)
                # mp_drawing.draw_landmarks(
                #     image=frame,
                #     landmark_list=results.multi_face_landmarks[0],
                #     connections=mp_face_mesh.FACEMESH_TESSELATION,
                #     landmark_drawing_spec=None,
                #     connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style())

            # Display the resulting frame
            cv2.imshow('FR2: Drowsiness Detection', frame)

            if cv2.waitKey(1) == ord('q'):
                break

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    print("Shutting down...")
    cap.release()
    cv2.destroyAllWindows()
    print("Script finished.")
