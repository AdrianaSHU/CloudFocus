import cv2
import mediapipe as mp
import time

print("Starting face detection...")

# --- Configuration ---
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# --- MediaPipe Initialization ---
# Load the MediaPipe Face Detection model
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

try:
    # Initialize the camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: Could not open camera at index {CAMERA_INDEX}.")
        exit()

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    print("Camera opened. Press 'q' to quit.")

    # --- Main Loop ---
    # Use the FaceDetection model as a context manager
    with mp_face_detection.FaceDetection(
        model_selection=0, min_detection_confidence=0.5) as face_detection:

        while True:
            # Capture frame-by-frame
            ret, frame = cap.read()
            if not ret:
                print("Error: Can't receive frame. Exiting ...")
                break

            # --- Face Detection Logic ---
            # 1. MediaPipe works with RGB, but OpenCV reads in BGR. Convert it.
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 2. Process the frame to find faces
            results = face_detection.process(frame_rgb)

            # 3. Draw bounding boxes on the *original* (BGR) frame
            if results.detections:
                for detection in results.detections:
                    # 'detection' contains a bounding box. Let's draw it.
                    # We get the bounding box location data
                    bboxC = detection.location_data.relative_bounding_box
                    ih, iw, _ = frame.shape
                    
                    # Calculate absolute pixel coordinates
                    xmin = int(bboxC.xmin * iw)
                    ymin = int(bboxC.ymin * ih)
                    w = int(bboxC.width * iw)
                    h = int(bboxC.height * ih)
                    
                    # Draw the rectangle on the BGR frame
                    cv2.rectangle(frame, (xmin, ymin), (xmin + w, ymin + h), (0, 255, 0), 2)
                    
                    # Optionally, add a confidence score
                    cv2.putText(frame, f'{int(detection.score[0] * 100)}%', 
                                (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                                0.6, (0, 255, 0), 2)


            # Display the resulting frame
            cv2.imshow('FR2: Face Detection', frame)

            # Wait for 1ms and check if 'q' is pressed
            if cv2.waitKey(1) == ord('q'):
                break

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # --- Cleanup ---
    print("Shutting down...")
    cap.release()
    cv2.destroyAllWindows()
    print("Script finished.")
