import cv2
import time

print("Starting camera test...")

# --- Configuration ---
# Try 0 for a built-in/USB webcam. 
# If using a Pi Camera Module, you might need to try -1 or 1.
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# --- Initialization ---
try:
    # Initialize the camera capture object
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print(f"Error: Could not open camera at index {CAMERA_INDEX}.")
        print("Please check if the camera is connected properly.")
        print("If using a Pi Camera, ensure it's enabled in 'sudo raspi-config'")
        exit()

    # Set desired frame width and height
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    # Allow the camera to warm up
    print("Camera warming up...")
    time.sleep(2)

    # Read one frame to get the actual dimensions
    ret, frame = cap.read()
    if ret:
        h, w, _ = frame.shape
        print(f"Camera opened successfully.")
        print(f"Requested resolution: {FRAME_WIDTH}x{FRAME_HEIGHT}")
        print(f"Actual resolution:   {w}x{h}")
    else:
        print("Error: Could not read a frame from the camera.")
        cap.release()
        exit()

    # --- Main Loop ---
    print("Displaying video feed. Press 'q' to quit.")
    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()

        # if frame is read correctly ret is True
        if not ret:
            print("Error: Can't receive frame (stream end?). Exiting ...")
            break

        # Display the resulting frame in a window
        cv2.imshow('FR1: Video Capture Test', frame)

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
    print("Camera test finished.")
    