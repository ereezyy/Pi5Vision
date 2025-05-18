#!/usr/bin/env python3
"""
Face enrollment script for Raspberry Pi 5 Face Recognition System with Hailo AI HAT+
This script allows users to add known faces to the database
"""

import os
import sys
import time
import argparse
import cv2
import numpy as np
import logging
from pathlib import Path

# Import our modules
from face_recognition import FaceProcessor, simulate_embedding_generation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('face_enrollment')

def capture_face(camera_device=0, resolution=(1280, 720)):
    """
    Capture a face image from the camera
    
    Args:
        camera_device: Camera device ID or path
        resolution: Camera resolution (width, height)
        
    Returns:
        Face image or None if canceled
    """
    # Initialize camera
    camera = cv2.VideoCapture(camera_device)
    if not camera.isOpened():
        logger.error(f"Failed to open camera device {camera_device}")
        return None
    
    # Set camera properties
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
    
    # Load face detector
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    face_img = None
    
    print("Press SPACE to capture, ESC to cancel")
    
    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                time.sleep(0.1)
                continue
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # Draw rectangle around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Display the frame
            cv2.imshow("Face Enrollment", frame)
            
            # Check for key press
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                print("Canceled")
                break
            elif key == 32:  # SPACE
                if len(faces) == 0:
                    print("No face detected. Please try again.")
                    continue
                
                if len(faces) > 1:
                    print("Multiple faces detected. Please ensure only one face is in the frame.")
                    continue
                
                # Get the largest face
                x, y, w, h = faces[0]
                face_img = frame[y:y+h, x:x+w]
                print("Face captured!")
                break
    
    finally:
        # Clean up
        camera.release()
        cv2.destroyAllWindows()
    
    return face_img

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Face Enrollment for Raspberry Pi 5 Face Recognition System")
    parser.add_argument("--db", type=str, default="/opt/pi5-face-recognition/database/faces.db", 
                       help="Path to face database")
    parser.add_argument("--faces-dir", type=str, default="/opt/pi5-face-recognition/faces", 
                       help="Directory to store face images")
    parser.add_argument("--alert-dir", type=str, default="/opt/pi5-face-recognition/alerts", 
                       help="Directory to store alert images")
    parser.add_argument("--camera", type=str, default="/dev/video0", 
                       help="Camera device path")
    args = parser.parse_args()
    
    # Ensure paths are absolute
    db_path = os.path.abspath(args.db)
    faces_dir = os.path.abspath(args.faces_dir)
    alert_dir = os.path.abspath(args.alert_dir)
    
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(faces_dir, exist_ok=True)
    os.makedirs(alert_dir, exist_ok=True)
    
    logger.info(f"Starting face enrollment with database {db_path}")
    
    try:
        # Initialize face processor
        processor = FaceProcessor(db_path, alert_dir, faces_dir)
        
        while True:
            # Get name for the face
            name = input("\nEnter name for the face (or 'q' to quit): ")
            if name.lower() == 'q':
                break
            
            # Capture face
            face_img = capture_face(args.camera)
            if face_img is None:
                continue
            
            # Add face to database
            person_id = processor.add_new_face(name, face_img)
            
            print(f"Added {name} to the database with ID {person_id}")
            
            # Ask if user wants to add another face
            another = input("Add another face? (y/n): ")
            if another.lower() != 'y':
                break
        
        print("\nFace enrollment completed.")
        return 0
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    finally:
        # Clean up
        if 'processor' in locals():
            processor.close()


if __name__ == "__main__":
    sys.exit(main())
