#!/usr/bin/env python3
"""
Real-time USB camera stream processing for Raspberry Pi 5 with Hailo AI HAT+
This module handles camera capture and integration with the Hailo accelerator
for face detection and recognition.
"""

import os
import sys
import time
import argparse
import cv2
import numpy as np
import subprocess
import threading
import queue
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('camera_stream')

class CameraStream:
    """
    Handles USB camera capture and processing for face recognition
    """
    def __init__(self, device_id=0, resolution=(1280, 720), fps=30):
        """
        Initialize the camera stream
        
        Args:
            device_id: Camera device ID (default: 0)
            resolution: Tuple of (width, height) (default: 1280x720)
            fps: Frames per second (default: 30)
        """
        self.device_id = device_id
        self.resolution = resolution
        self.fps = fps
        self.camera = None
        self.is_running = False
        self.frame_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue()
        self.processing_thread = None
        
        logger.info(f"Initializing camera stream with device {device_id}, "
                   f"resolution {resolution}, fps {fps}")
    
    def start(self):
        """Start the camera stream and processing thread"""
        if self.is_running:
            logger.warning("Camera stream is already running")
            return
        
        # Initialize camera
        self.camera = cv2.VideoCapture(self.device_id)
        if not self.camera.isOpened():
            raise RuntimeError(f"Failed to open camera device {self.device_id}")
        
        # Set camera properties
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        self.camera.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Start processing thread
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._process_frames)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("Camera stream started")
    
    def stop(self):
        """Stop the camera stream and processing thread"""
        if not self.is_running:
            logger.warning("Camera stream is not running")
            return
        
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
        
        if self.camera:
            self.camera.release()
            self.camera = None
        
        logger.info("Camera stream stopped")
    
    def _process_frames(self):
        """Process frames from the camera (runs in a separate thread)"""
        while self.is_running:
            ret, frame = self.camera.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                time.sleep(0.1)
                continue
            
            # Add frame to queue, dropping oldest if full
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass
    
    def get_frame(self):
        """Get the latest frame from the camera"""
        try:
            return self.frame_queue.get(timeout=1.0)
        except queue.Empty:
            return None


class HailoFaceProcessor:
    """
    Process frames using Hailo AI accelerator for face detection and recognition
    """
    def __init__(self, model_path, confidence_threshold=0.5):
        """
        Initialize the Hailo face processor
        
        Args:
            model_path: Path to the Hailo model file (.hef)
            confidence_threshold: Confidence threshold for detection (default: 0.5)
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.is_running = False
        self.processing_thread = None
        self.frame_queue = queue.Queue(maxsize=5)
        self.result_queue = queue.Queue(maxsize=10)
        
        # Verify model file exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        logger.info(f"Initializing Hailo face processor with model {model_path}")
        
        # Check Hailo device
        try:
            result = subprocess.run(
                ["hailortcli", "fw-control", "identify"],
                capture_output=True, text=True, check=True
            )
            logger.info(f"Hailo device identified: {result.stdout}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Failed to identify Hailo device: {e}")
            raise RuntimeError("Hailo device not found or not accessible")
    
    def start(self):
        """Start the face processing thread"""
        if self.is_running:
            logger.warning("Face processor is already running")
            return
        
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._process_frames)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("Hailo face processor started")
    
    def stop(self):
        """Stop the face processing thread"""
        if not self.is_running:
            logger.warning("Face processor is not running")
            return
        
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
        
        logger.info("Hailo face processor stopped")
    
    def process_frame(self, frame):
        """
        Add a frame to the processing queue
        
        Args:
            frame: OpenCV frame to process
        """
        if not self.is_running:
            logger.warning("Face processor is not running")
            return
        
        # Add frame to queue, dropping oldest if full
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        
        try:
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            pass
    
    def get_result(self, timeout=0.1):
        """
        Get the latest processing result
        
        Args:
            timeout: Timeout in seconds (default: 0.1)
            
        Returns:
            Tuple of (frame, detections) or None if no result is available
        """
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _process_frames(self):
        """Process frames using Hailo (runs in a separate thread)"""
        while self.is_running:
            try:
                frame = self.frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            # Process frame using GStreamer pipeline with Hailo
            # This is a placeholder - in the actual implementation, we would
            # use the Hailo API or GStreamer to process the frame
            # For now, we'll simulate processing with a delay
            time.sleep(0.05)
            
            # Simulate face detection results
            # In the actual implementation, this would be the output from Hailo
            detections = self._simulate_face_detection(frame)
            
            # Add result to queue, dropping oldest if full
            if self.result_queue.full():
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    pass
            
            try:
                self.result_queue.put_nowait((frame, detections))
            except queue.Full:
                pass
    
    def _simulate_face_detection(self, frame):
        """
        Simulate face detection (placeholder for actual Hailo processing)
        
        Args:
            frame: OpenCV frame
            
        Returns:
            List of face detections (x, y, w, h, confidence)
        """
        # This is just a placeholder - in the actual implementation,
        # we would use the Hailo API to detect faces
        # For demonstration purposes, we'll use OpenCV's face detector
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        # Convert to our detection format
        detections = []
        for (x, y, w, h) in faces:
            confidence = 0.9  # Simulated confidence
            detections.append((x, y, w, h, confidence))
        
        return detections


def run_gstreamer_pipeline(device="/dev/video0", model_path="/path/to/retinaface_mobilenet_v1.hef"):
    """
    Run the GStreamer pipeline for face detection using Hailo
    
    Args:
        device: Camera device path (default: /dev/video0)
        model_path: Path to the Hailo model file (.hef)
    """
    pipeline_cmd = [
        "gst-launch-1.0", "hailomuxer", "name=hmux",
        f"v4l2src device={device}", "!",
        "video/x-raw,format=NV12,width=1280,height=720,framerate=30/1", "!",
        "queue", "name=hailo_preprocess_q_0", "leaky=no", "max-size-buffers=30", "max-size-bytes=0", "max-size-time=0", "!",
        "videoscale", "qos=false", "n-threads=2", "!", "video/x-raw,", "pixel-aspect-ratio=1/1", "!",
        "queue", "leaky=no", "max-size-buffers=30", "max-size-bytes=0", "max-size-time=0", "!",
        "videoconvert", "n-threads=2", "qos=false", "!",
        "queue", "leaky=no", "max-size-buffers=30", "max-size-bytes=0", "max-size-time=0", "!",
        "hailonet", f"hef-path={model_path}", "!",
        "queue", "leaky=no", "max-size-buffers=30", "max-size-bytes=0", "max-size-time=0", "!",
        "hailofilter", "so-path=/usr/lib/aarch64-linux-gnu/post_processes/libface_detection_post.so", 
        "name=face_detection_hailofilter", "qos=false", "function_name=retinaface", "!",
        "queue", "leaky=no", "max-size-buffers=30", "max-size-bytes=0", "max-size-time=0", "!",
        "hailooverlay", "name=hailo_overlay", "qos=false", "show-confidence=false", 
        "line-thickness=5", "font-thickness=2", "!",
        "videoconvert", "!",
        "autovideosink"
    ]
    
    logger.info(f"Running GStreamer pipeline: {' '.join(pipeline_cmd)}")
    
    try:
        process = subprocess.Popen(
            pipeline_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the process to complete or be terminated
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"GStreamer pipeline failed with return code {process.returncode}")
            logger.error(f"Error output: {stderr}")
        else:
            logger.info("GStreamer pipeline completed successfully")
        
        return process.returncode == 0
    
    except Exception as e:
        logger.error(f"Failed to run GStreamer pipeline: {e}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Raspberry Pi 5 Face Recognition with Hailo AI HAT+")
    parser.add_argument("--device", type=str, default="/dev/video0", help="Camera device path")
    parser.add_argument("--model", type=str, required=True, help="Path to Hailo model file (.hef)")
    parser.add_argument("--mode", type=str, choices=["gstreamer", "opencv"], default="gstreamer",
                       help="Processing mode (gstreamer or opencv)")
    args = parser.parse_args()
    
    logger.info(f"Starting face recognition with device {args.device}, model {args.model}, mode {args.mode}")
    
    try:
        if args.mode == "gstreamer":
            # Run GStreamer pipeline directly
            success = run_gstreamer_pipeline(device=args.device, model_path=args.model)
            if not success:
                logger.error("GStreamer pipeline failed")
                return 1
        
        elif args.mode == "opencv":
            # Use OpenCV with Hailo processing
            camera = CameraStream(device_id=args.device)
            processor = HailoFaceProcessor(model_path=args.model)
            
            camera.start()
            processor.start()
            
            try:
                while True:
                    frame = camera.get_frame()
                    if frame is None:
                        continue
                    
                    processor.process_frame(frame)
                    result = processor.get_result()
                    
                    if result:
                        processed_frame, detections = result
                        
                        # Draw detection results
                        for x, y, w, h, conf in detections:
                            cv2.rectangle(processed_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            cv2.putText(processed_frame, f"{conf:.2f}", (x, y-10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
                        # Display the frame
                        cv2.imshow("Face Recognition", processed_frame)
                        
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
            
            finally:
                camera.stop()
                processor.stop()
                cv2.destroyAllWindows()
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
