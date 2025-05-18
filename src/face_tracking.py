#!/usr/bin/env python3
"""
Face tracking and alert system for Raspberry Pi 5 with Hailo AI HAT+
This module integrates camera stream processing with face recognition
and provides a complete tracking and alerting system.
"""

import os
import sys
import time
import argparse
import cv2
import numpy as np
import threading
import queue
import logging
import json
from datetime import datetime
from pathlib import Path
import signal

# Import our modules
from camera_stream import CameraStream, HailoFaceProcessor, run_gstreamer_pipeline
from face_recognition import FaceProcessor, simulate_embedding_generation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('face_tracking.log')
    ]
)
logger = logging.getLogger('face_tracking')

class FaceTrackingSystem:
    """
    Integrates camera stream, face detection, recognition, and alerting
    """
    def __init__(self, config):
        """
        Initialize the face tracking system
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.base_dir = config.get('base_dir', os.path.abspath('.'))
        
        # Create necessary directories
        self.db_dir = os.path.join(self.base_dir, 'database')
        self.alert_dir = os.path.join(self.base_dir, 'alerts')
        self.faces_dir = os.path.join(self.base_dir, 'faces')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        
        for directory in [self.db_dir, self.alert_dir, self.faces_dir, self.logs_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Initialize components
        self.db_path = os.path.join(self.db_dir, 'faces.db')
        self.camera = None
        self.face_processor = None
        self.hailo_processor = None
        
        # Threading and synchronization
        self.is_running = False
        self.processing_thread = None
        self.display_thread = None
        self.frame_queue = queue.Queue(maxsize=5)
        self.result_queue = queue.Queue(maxsize=10)
        
        logger.info(f"Face tracking system initialized with base directory: {self.base_dir}")
    
    def setup(self):
        """Set up all components of the system"""
        try:
            # Initialize face processor
            self.face_processor = FaceProcessor(
                self.db_path,
                self.alert_dir,
                self.faces_dir
            )
            
            # Initialize camera
            if self.config.get('use_gstreamer', True):
                logger.info("Using GStreamer pipeline for camera and Hailo processing")
                # GStreamer pipeline will be run separately
                self.camera = None
            else:
                logger.info("Using OpenCV for camera capture")
                self.camera = CameraStream(
                    device_id=self.config.get('camera_device', 0),
                    resolution=self.config.get('resolution', (1280, 720)),
                    fps=self.config.get('fps', 30)
                )
                
                # Initialize Hailo processor
                self.hailo_processor = HailoFaceProcessor(
                    model_path=self.config.get('model_path'),
                    confidence_threshold=self.config.get('confidence_threshold', 0.5)
                )
            
            logger.info("System setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up system: {e}")
            return False
    
    def start(self):
        """Start the face tracking system"""
        if self.is_running:
            logger.warning("System is already running")
            return False
        
        try:
            self.is_running = True
            
            if self.config.get('use_gstreamer', True):
                # Run GStreamer pipeline in a separate thread
                self.processing_thread = threading.Thread(
                    target=self._run_gstreamer_pipeline
                )
                self.processing_thread.daemon = True
                self.processing_thread.start()
            else:
                # Start camera and Hailo processor
                self.camera.start()
                self.hailo_processor.start()
                
                # Start processing thread
                self.processing_thread = threading.Thread(
                    target=self._process_frames
                )
                self.processing_thread.daemon = True
                self.processing_thread.start()
                
                # Start display thread
                self.display_thread = threading.Thread(
                    target=self._display_results
                )
                self.display_thread.daemon = True
                self.display_thread.start()
            
            logger.info("Face tracking system started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            self.is_running = False
            return False
    
    def stop(self):
        """Stop the face tracking system"""
        if not self.is_running:
            logger.warning("System is not running")
            return
        
        self.is_running = False
        
        # Wait for threads to finish
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        if self.display_thread:
            self.display_thread.join(timeout=2.0)
        
        # Stop components
        if self.camera:
            self.camera.stop()
        
        if self.hailo_processor:
            self.hailo_processor.stop()
        
        if self.face_processor:
            self.face_processor.close()
        
        logger.info("Face tracking system stopped")
    
    def _run_gstreamer_pipeline(self):
        """Run the GStreamer pipeline for camera and Hailo processing"""
        try:
            device = self.config.get('camera_device', '/dev/video0')
            model_path = self.config.get('model_path')
            
            logger.info(f"Running GStreamer pipeline with device {device} and model {model_path}")
            
            success = run_gstreamer_pipeline(device=device, model_path=model_path)
            
            if not success:
                logger.error("GStreamer pipeline failed")
                self.is_running = False
            
        except Exception as e:
            logger.error(f"Error in GStreamer pipeline: {e}")
            self.is_running = False
    
    def _process_frames(self):
        """Process frames from camera with Hailo and face recognition"""
        while self.is_running:
            try:
                # Get frame from camera
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                # Process with Hailo
                self.hailo_processor.process_frame(frame)
                hailo_result = self.hailo_processor.get_result()
                
                if hailo_result:
                    processed_frame, detections = hailo_result
                    
                    # Process detections with face recognition
                    recognition_results = self.face_processor.process_detections(
                        processed_frame, 
                        detections, 
                        simulate_embedding_generation
                    )
                    
                    # Add to result queue
                    if self.result_queue.full():
                        try:
                            self.result_queue.get_nowait()
                        except queue.Empty:
                            pass
                    
                    try:
                        self.result_queue.put_nowait((processed_frame, recognition_results))
                    except queue.Full:
                        pass
            
            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                time.sleep(0.1)
    
    def _display_results(self):
        """Display processing results"""
        while self.is_running:
            try:
                # Get result from queue
                result = self.result_queue.get(timeout=0.5)
                if result is None:
                    continue
                
                frame, recognition_results = result
                
                # Draw recognition results
                for detection in recognition_results:
                    x, y, w, h = detection['x'], detection['y'], detection['w'], detection['h']
                    
                    # Different colors for known vs unknown faces
                    if detection.get('recognized', False):
                        color = (0, 255, 0)  # Green for known faces
                        name = detection.get('name', 'Unknown')
                        similarity = detection.get('similarity', 0.0)
                        label = f"{name} ({similarity:.2f})"
                    else:
                        color = (0, 0, 255)  # Red for unknown faces
                        name = detection.get('name', 'Unknown')
                        label = name
                    
                    # Draw bounding box
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                    
                    # Draw label
                    cv2.putText(frame, label, (x, y-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # Display the frame
                cv2.imshow("Face Recognition", frame)
                
                # Check for key press
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("User requested exit")
                    self.is_running = False
                    break
                elif key == ord('a'):
                    # Add current face as known (placeholder)
                    logger.info("Add face functionality triggered")
            
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error displaying results: {e}")
                time.sleep(0.1)
    
    def add_known_face(self, name, face_img):
        """
        Add a known face to the database
        
        Args:
            name: Person's name
            face_img: Face image
            
        Returns:
            Person ID
        """
        if self.face_processor:
            return self.face_processor.add_new_face(name, face_img)
        return None


class WebInterface:
    """
    Simple web interface for the face tracking system
    """
    def __init__(self, tracking_system, host='0.0.0.0', port=8080):
        """
        Initialize the web interface
        
        Args:
            tracking_system: FaceTrackingSystem instance
            host: Host to bind to (default: 0.0.0.0)
            port: Port to bind to (default: 8080)
        """
        self.tracking_system = tracking_system
        self.host = host
        self.port = port
        self.server = None
        
        logger.info(f"Web interface initialized on {host}:{port}")
    
    def start(self):
        """Start the web interface"""
        # This is a placeholder for a real web interface
        # In a real implementation, we would use Flask or FastAPI
        logger.info(f"Web interface started on http://{self.host}:{self.port}")
        logger.info("Note: This is a placeholder for a real web interface")
    
    def stop(self):
        """Stop the web interface"""
        logger.info("Web interface stopped")


def signal_handler(sig, frame):
    """Handle signals for graceful shutdown"""
    logger.info("Received shutdown signal")
    if 'tracking_system' in globals():
        tracking_system.stop()
    sys.exit(0)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Face Tracking and Alert System")
    parser.add_argument("--config", type=str, default="config.json", help="Path to configuration file")
    parser.add_argument("--base-dir", type=str, default=".", help="Base directory for data storage")
    parser.add_argument("--camera", type=str, default="/dev/video0", help="Camera device path")
    parser.add_argument("--model", type=str, required=True, help="Path to Hailo model file (.hef)")
    parser.add_argument("--gstreamer", action="store_true", help="Use GStreamer pipeline")
    parser.add_argument("--web", action="store_true", help="Enable web interface")
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load configuration
    config = {
        'base_dir': os.path.abspath(args.base_dir),
        'camera_device': args.camera,
        'model_path': args.model,
        'use_gstreamer': args.gstreamer,
        'resolution': (1280, 720),
        'fps': 30,
        'confidence_threshold': 0.5
    }
    
    # Try to load config from file
    if os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
            logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.warning(f"Failed to load configuration from {args.config}: {e}")
    
    logger.info(f"Starting face tracking system with configuration: {json.dumps(config, indent=2)}")
    
    try:
        # Initialize tracking system
        global tracking_system
        tracking_system = FaceTrackingSystem(config)
        
        # Set up system
        if not tracking_system.setup():
            logger.error("Failed to set up tracking system")
            return 1
        
        # Start tracking
        if not tracking_system.start():
            logger.error("Failed to start tracking system")
            return 1
        
        # Start web interface if requested
        web_interface = None
        if args.web:
            web_interface = WebInterface(tracking_system)
            web_interface.start()
        
        # Keep running until interrupted
        logger.info("System running. Press Ctrl+C to exit.")
        while tracking_system.is_running:
            time.sleep(1.0)
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    finally:
        # Clean up
        if 'tracking_system' in locals():
            tracking_system.stop()
        
        if 'web_interface' in locals() and web_interface:
            web_interface.stop()
        
        cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.exit(main())
