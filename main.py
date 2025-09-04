import cv2
import mediapipe as mp
import numpy as np
import time

# MediaPipe setup
BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
FaceLandmarkerResult = mp.tasks.vision.FaceLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

# Define face oval (silhouette) landmark indices for polygon drawing
FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400,
             377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]

# Load the Face Landmarker model with blendshapes enabled for expressions
options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='face_landmarker.task'),
    running_mode=VisionRunningMode.VIDEO,
    output_face_blendshapes=True,
    num_faces=1  # Detect one face for simplicity/efficiency
)

landmarker = FaceLandmarker.create_from_options(options)

# Start video capture from webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

# Get frame dimensions for video writer (or hardcode if needed)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = 30  # Approximate FPS

# Set up video writer to save output (MP4 format)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4
out = cv2.VideoWriter('output_video.mp4', fourcc, fps, (frame_width, frame_height))

# Manual timestamp for video mode
timestamp_ms = 0
frame_time_ms = int(1000 / fps)  # e.g., 33 ms for 30 FPS

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame from webcam.")
        break

    # Convert frame to MediaPipe Image (RGB format)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    # Perform face landmark detection
    results = landmarker.detect_for_video(mp_image, timestamp_ms)
    timestamp_ms += frame_time_ms  # Increment timestamp for next frame

    # Process results if a face is detected
    if results.face_landmarks:
        # Get landmarks for the first (only) face
        face_landmarks = results.face_landmarks[0]

        # Collect points for the face oval polygon
        points = []
        for idx in FACE_OVAL:
            lm = face_landmarks[idx]
            x = int(lm.x * frame.shape[1])  # Denormalize x
            y = int(lm.y * frame.shape[0])  # Denormalize y
            points.append((x, y))

        # Draw the polygon around the face (blue, thickness 2)
        if points:
            cv2.polylines(frame, [np.array(points)], isClosed=True, color=(255, 0, 0), thickness=2)

        # Analyze facial expression using blendshapes
        if results.face_blendshapes:
            blendshapes = results.face_blendshapes[0]  # For the first face
            # Extract key blendshape scores (values range 0-1)
            smile_left = next((bs.score for bs in blendshapes if bs.category_name == 'mouthSmileLeft'), 0)
            smile_right = next((bs.score for bs in blendshapes if bs.category_name == 'mouthSmileRight'), 0)
            frown_left = next((bs.score for bs in blendshapes if bs.category_name == 'mouthFrownLeft'), 0)
            brow_down = next((bs.score for bs in blendshapes if bs.category_name == 'browDownLeft'), 0)
            jaw_open = next((bs.score for bs in blendshapes if bs.category_name == 'jawOpen'), 0)
            eye_wide = next((bs.score for bs in blendshapes if bs.category_name == 'eyeWideLeft'), 0)

            # Simple expression classification (threshold-based)
            expression = "Neutral"
            if smile_left > 0.5 and smile_right > 0.5:
                expression = "Happy"
            elif frown_left > 0.5:
                expression = "Sad"
            elif brow_down > 0.5:
                expression = "Angry"
            elif jaw_open > 0.5 and eye_wide > 0.5:
                expression = "Surprised"

            # Display reaction text on the frame
            cv2.putText(frame, f"You seem {expression}!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Write the processed frame to the output video
    out.write(frame)

    # Display the frame
    cv2.imshow('Advanced Face Detection with Expressions', frame)

    # Exit on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
out.release()
cv2.destroyAllWindows()