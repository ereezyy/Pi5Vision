#!/usr/bin/env python3
"""
Web Dashboard for Raspberry Pi 5 Face Recognition System with Hailo AI HAT+
This module provides a modern, responsive web interface for the face recognition system
"""

import os
import sys
import time
import logging
import json
import threading
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Import FastAPI components
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import core engine
from core_engine import CoreEngine, ModelManager, FaceAnalytics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('web_dashboard')

# Define data models
class PersonModel(BaseModel):
    """Person data model"""
    id: str
    name: str
    first_seen: datetime
    last_seen: datetime
    visit_count: int
    notes: Optional[str] = None
    image_path: Optional[str] = None

class FaceEmbeddingModel(BaseModel):
    """Face embedding data model"""
    id: str
    person_id: str
    created_at: datetime
    image_path: Optional[str] = None

class AlertModel(BaseModel):
    """Alert data model"""
    id: str
    person_id: Optional[str] = None
    timestamp: datetime
    alert_type: str
    image_path: Optional[str] = None
    processed: bool = False

class RecognitionResultModel(BaseModel):
    """Recognition result data model"""
    timestamp: datetime
    frame_id: str
    num_faces: int
    faces: List[Dict[str, Any]]

class SystemStatusModel(BaseModel):
    """System status data model"""
    uptime: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    temperature: float
    camera_status: str
    hailo_status: str
    model_status: Dict[str, str]
    last_updated: datetime

class WebDashboard:
    """
    Web dashboard for the face recognition system
    """
    def __init__(self, config_path: str = None):
        """
        Initialize the web dashboard
        
        Args:
            config_path: Path to configuration file (optional)
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Set up directories
        self.base_dir = Path(self.config.get('base_dir', '/opt/pi5-face-recognition'))
        self.static_dir = self.base_dir / 'static'
        self.templates_dir = self.base_dir / 'templates'
        self.faces_dir = self.base_dir / 'faces'
        self.alerts_dir = self.base_dir / 'alerts'
        
        # Ensure directories exist
        for directory in [self.static_dir, self.templates_dir, self.faces_dir, self.alerts_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Pi5 Face Recognition Dashboard",
            description="Web dashboard for Raspberry Pi 5 Face Recognition System with Hailo AI HAT+",
            version="2.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize templates
        self.templates = Jinja2Templates(directory=str(self.templates_dir))
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")
        self.app.mount("/faces", StaticFiles(directory=str(self.faces_dir)), name="faces")
        self.app.mount("/alerts", StaticFiles(directory=str(self.alerts_dir)), name="alerts")
        
        # Initialize core engine
        self.core_engine = CoreEngine(config_path)
        
        # Initialize WebSocket connection manager
        self.connection_manager = ConnectionManager()
        
        # Set up routes
        self._setup_routes()
        
        # Background tasks
        self.background_tasks = BackgroundTasks()
        
        # System status
        self.system_status = {
            'uptime': 0,
            'cpu_usage': 0,
            'memory_usage': 0,
            'disk_usage': 0,
            'temperature': 0,
            'camera_status': 'unknown',
            'hailo_status': 'unknown',
            'model_status': {},
            'last_updated': datetime.now()
        }
        
        # Start time for uptime calculation
        self.start_time = time.time()
        
        logger.info("Web dashboard initialized")
    
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """
        Load configuration from file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        # Default configuration
        config = {
            'base_dir': '/opt/pi5-face-recognition',
            'host': '0.0.0.0',
            'port': 8080,
            'debug': False,
            'enable_authentication': False,
            'username': 'admin',
            'password': 'admin',
            'session_timeout': 3600,  # 1 hour
            'ssl_cert': None,
            'ssl_key': None
        }
        
        # Load from file if provided
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load configuration from {config_path}: {e}")
        
        return config
    
    def _setup_routes(self):
        """Set up API routes"""
        # Main routes
        @self.app.get("/", response_class=HTMLResponse)
        async def get_index():
            """Serve the main dashboard page"""
            return self.templates.TemplateResponse("index.html", {"request": {}})
        
        @self.app.get("/api/status", response_model=SystemStatusModel)
        async def get_status():
            """Get system status"""
            # Update system status
            await self._update_system_status()
            return self.system_status
        
        # WebSocket for real-time updates
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await self.connection_manager.connect(websocket)
            try:
                while True:
                    # Receive message from client
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle message
                    if message.get('type') == 'ping':
                        await websocket.send_text(json.dumps({'type': 'pong'}))
                    elif message.get('type') == 'subscribe':
                        # Subscribe to events
                        topics = message.get('topics', [])
                        for topic in topics:
                            self.connection_manager.subscribe(websocket, topic)
                        await websocket.send_text(json.dumps({
                            'type': 'subscribed',
                            'topics': topics
                        }))
                    elif message.get('type') == 'unsubscribe':
                        # Unsubscribe from events
                        topics = message.get('topics', [])
                        for topic in topics:
                            self.connection_manager.unsubscribe(websocket, topic)
                        await websocket.send_text(json.dumps({
                            'type': 'unsubscribed',
                            'topics': topics
                        }))
            except WebSocketDisconnect:
                self.connection_manager.disconnect(websocket)
        
        # Person management
        @self.app.get("/api/persons", response_model=List[PersonModel])
        async def get_persons(
            limit: int = Query(100, ge=1, le=1000),
            offset: int = Query(0, ge=0)
        ):
            """Get list of persons"""
            # This is a placeholder - in a real implementation, we would query the database
            persons = []
            for i in range(min(10, limit)):
                person_id = f"person_{i+1+offset}"
                persons.append({
                    'id': person_id,
                    'name': f"Person {i+1+offset}",
                    'first_seen': datetime.now() - timedelta(days=i),
                    'last_seen': datetime.now() - timedelta(hours=i),
                    'visit_count': 10 - i,
                    'notes': f"Note for person {i+1+offset}" if i % 2 == 0 else None,
                    'image_path': f"/faces/{person_id}.jpg" if i % 2 == 0 else None
                })
            return persons
        
        @self.app.get("/api/persons/{person_id}", response_model=PersonModel)
        async def get_person(person_id: str):
            """Get person by ID"""
            # This is a placeholder - in a real implementation, we would query the database
            if not person_id.startswith("person_"):
                raise HTTPException(status_code=404, detail="Person not found")
            
            person_num = int(person_id.split("_")[1])
            return {
                'id': person_id,
                'name': f"Person {person_num}",
                'first_seen': datetime.now() - timedelta(days=person_num),
                'last_seen': datetime.now() - timedelta(hours=person_num),
                'visit_count': 10 - person_num,
                'notes': f"Note for person {person_num}" if person_num % 2 == 0 else None,
                'image_path': f"/faces/{person_id}.jpg" if person_num % 2 == 0 else None
            }
        
        # Alert management
        @self.app.get("/api/alerts", response_model=List[AlertModel])
        async def get_alerts(
            limit: int = Query(100, ge=1, le=1000),
            offset: int = Query(0, ge=0),
            processed: Optional[bool] = None
        ):
            """Get list of alerts"""
            # This is a placeholder - in a real implementation, we would query the database
            alerts = []
            for i in range(min(10, limit)):
                alert_id = f"alert_{i+1+offset}"
                person_id = f"person_{i+1}" if i % 3 != 0 else None
                alert_processed = i % 2 == 0
                
                if processed is not None and alert_processed != processed:
                    continue
                
                alerts.append({
                    'id': alert_id,
                    'person_id': person_id,
                    'timestamp': datetime.now() - timedelta(hours=i),
                    'alert_type': 'new_face' if person_id else 'unknown_face',
                    'image_path': f"/alerts/{alert_id}.jpg",
                    'processed': alert_processed
                })
            return alerts
        
        @self.app.get("/api/alerts/{alert_id}", response_model=AlertModel)
        async def get_alert(alert_id: str):
            """Get alert by ID"""
            # This is a placeholder - in a real implementation, we would query the database
            if not alert_id.startswith("alert_"):
                raise HTTPException(status_code=404, detail="Alert not found")
            
            alert_num = int(alert_id.split("_")[1])
            person_id = f"person_{alert_num}" if alert_num % 3 != 0 else None
            
            return {
                'id': alert_id,
                'person_id': person_id,
                'timestamp': datetime.now() - timedelta(hours=alert_num),
                'alert_type': 'new_face' if person_id else 'unknown_face',
                'image_path': f"/alerts/{alert_id}.jpg",
                'processed': alert_num % 2 == 0
            }
        
        @self.app.post("/api/alerts/{alert_id}/process")
        async def process_alert(alert_id: str):
            """Mark alert as processed"""
            # This is a placeholder - in a real implementation, we would update the database
            if not alert_id.startswith("alert_"):
                raise HTTPException(status_code=404, detail="Alert not found")
            
            return {"status": "success", "message": f"Alert {alert_id} marked as processed"}
        
        # Video streaming
        @self.app.get("/api/stream")
        async def video_stream():
            """Stream video from camera"""
            return StreamingResponse(self._generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")
        
        # Recognition results
        @self.app.get("/api/recognition", response_model=List[RecognitionResultModel])
        async def get_recognition_results(
            limit: int = Query(10, ge=1, le=100),
            offset: int = Query(0, ge=0)
        ):
            """Get recent recognition results"""
            # This is a placeholder - in a real implementation, we would query the database
            results = []
            for i in range(min(10, limit)):
                frame_id = f"frame_{i+1+offset}"
                num_faces = i % 3 + 1
                
                faces = []
                for j in range(num_faces):
                    person_id = f"person_{j+1}" if j % 2 == 0 else None
                    faces.append({
                        'bbox': [100, 100, 200, 200],
                        'confidence': 0.9 - (j * 0.1),
                        'person_id': person_id,
                        'name': f"Person {j+1}" if person_id else "Unknown",
                        'similarity': 0.85 - (j * 0.1) if person_id else None
                    })
                
                results.append({
                    'timestamp': datetime.now() - timedelta(seconds=i*10),
                    'frame_id': frame_id,
                    'num_faces': num_faces,
                    'faces': faces
                })
            
            return results
        
        # Analytics
        @self.app.get("/api/analytics/visitors")
        async def get_visitor_analytics():
            """Get visitor analytics"""
            # This is a placeholder - in a real implementation, we would query the database
            return {
                'total_visitors': 100,
                'known_visitors': 75,
                'unknown_visitors': 25,
                'visits_by_hour': [i % 10 for i in range(24)],
                'visits_by_day': [10, 15, 20, 25, 15, 5, 10],
                'visits_by_month': [i * 5 for i in range(12)],
                'gender_stats': {'male': 60, 'female': 40, 'unknown': 0},
                'age_groups': {'0-18': 10, '19-35': 40, '36-50': 30, '51+': 20},
                'emotion_stats': {
                    'neutral': 50, 'happy': 30, 'sad': 5, 'angry': 5, 
                    'surprised': 5, 'fearful': 3, 'disgusted': 2
                }
            }
        
        # System management
        @self.app.post("/api/system/restart")
        async def restart_system():
            """Restart the face recognition system"""
            # This is a placeholder - in a real implementation, we would restart the system
            return {"status": "success", "message": "System restarting..."}
        
        @self.app.post("/api/system/shutdown")
        async def shutdown_system():
            """Shutdown the face recognition system"""
            # This is a placeholder - in a real implementation, we would shutdown the system
            return {"status": "success", "message": "System shutting down..."}
    
    async def _update_system_status(self):
        """Update system status"""
        try:
            # Calculate uptime
            self.system_status['uptime'] = time.time() - self.start_time
            
            # Get CPU usage
            self.system_status['cpu_usage'] = self._get_cpu_usage()
            
            # Get memory usage
            self.system_status['memory_usage'] = self._get_memory_usage()
            
            # Get disk usage
            self.system_status['disk_usage'] = self._get_disk_usage()
            
            # Get temperature
            self.system_status['temperature'] = self._get_temperature()
            
            # Get camera status
            self.system_status['camera_status'] = self._get_camera_status()
            
            # Get Hailo status
            self.system_status['hailo_status'] = self._get_hailo_status()
            
            # Get model status
            self.system_status['model_status'] = self._get_model_status()
            
            # Update timestamp
            self.system_status['last_updated'] = datetime.now()
        
        except Exception as e:
            logger.error(f"Error updating system status: {e}")
    
    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return float(np.random.uniform(10, 30))  # Simulated value
    
    def _get_memory_usage(self) -> float:
        """Get memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return float(np.random.uniform(20, 50))  # Simulated value
    
    def _get_disk_usage(self) -> float:
        """Get disk usage percentage"""
        try:
            import psutil
            return psutil.disk_usage('/').percent
        except ImportError:
            return float(np.random.uniform(30, 70))  # Simulated value
    
    def _get_temperature(self) -> float:
        """Get CPU temperature"""
        try:
            # Try to read temperature from Raspberry Pi
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
            return temp
        except:
            return float(np.random.uniform(40, 60))  # Simulated value
    
    def _get_camera_status(self) -> str:
        """Get camera status"""
        # This is a placeholder - in a real implementation, we would check the camera
        return "connected"
    
    def _get_hailo_status(self) -> str:
        """Get Hailo status"""
        # This is a placeholder - in a real implementation, we would check the Hailo device
        return "connected"
    
    def _get_model_status(self) -> Dict[str, str]:
        """Get model status"""
        # This is a placeholder - in a real implementation, we would check the models
        return {
            'face_detection_primary': 'loaded',
            'face_detection_secondary': 'loaded',
            'face_recognition': 'loaded',
            'age_gender': 'loaded',
            'emotion': 'loaded'
        }
    
    async def _generate_frames(self):
        """Generate video frames for streaming"""
        # This is a placeholder - in a real implementation, we would capture frames from the camera
        import numpy as np
        import cv2
        
        while True:
            # Create a blank frame
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            # Yield frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Wait
            await asyncio.sleep(0.1)
    
    def run(self):
        """Run the web dashboard"""
        import uvicorn
        
        # Initialize core engine
        asyncio.run(self.core_engine.initialize())
        
        # Start core engine
        self.core_engine.start()
        
        # Run FastAPI app
        host = self.config.get('host', '0.0.0.0')
        port = self.config.get('port', 8080)
        debug = self.config.get('debug', False)
        
        ssl_cert = self.config.get('ssl_cert')
        ssl_key = self.config.get('ssl_key')
        
        if ssl_cert and ssl_key and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
            # Run with SSL
            uvicorn.run(
                self.app,
                host=host,
                port=port,
                ssl_certfile=ssl_cert,
                ssl_keyfile=ssl_key,
                log_level="info"
            )
        else:
            # Run without SSL
            uvicorn.run(
                self.app,
                host=host,
                port=port,
                log_level="info"
            )


class ConnectionManager:
    """
    WebSocket connection manager for real-time updates
    """
    def __init__(self):
        """Initialize the connection manager"""
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        """
        Connect a WebSocket client
        
        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket client
        
        Args:
            websocket: WebSocket connection
        """
        self.active_connections.remove(websocket)
        
        # Remove from subscriptions
        for topic in list(self.subscriptions.keys()):
            if websocket in self.subscriptions[topic]:
                self.subscriptions[topic].remove(websocket)
            
            # Clean up empty subscription lists
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
    
    def subscribe(self, websocket: WebSocket, topic: str):
        """
        Subscribe a WebSocket client to a topic
        
        Args:
            websocket: WebSocket connection
            topic: Topic to subscribe to
        """
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        
        if websocket not in self.subscriptions[topic]:
            self.subscriptions[topic].append(websocket)
    
    def unsubscribe(self, websocket: WebSocket, topic: str):
        """
        Unsubscribe a WebSocket client from a topic
        
        Args:
            websocket: WebSocket connection
            topic: Topic to unsubscribe from
        """
        if topic in self.subscriptions and websocket in self.subscriptions[topic]:
            self.subscriptions[topic].remove(websocket)
            
            # Clean up empty subscription lists
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
    
    async def broadcast(self, topic: str, message: Any):
        """
        Broadcast a message to all subscribers of a topic
        
        Args:
            topic: Topic to broadcast to
            message: Message to broadcast
        """
        if topic not in self.subscriptions:
            return
        
        # Convert message to JSON
        if not isinstance(message, str):
            message = json.dumps(message)
        
        # Send to all subscribers
        for connection in self.subscriptions[topic]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")


# Import numpy for simulated values
import numpy as np

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web Dashboard for Raspberry Pi 5 Face Recognition System")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Create web dashboard
    dashboard = WebDashboard(args.config)
    
    # Override config with command line arguments
    if args.host:
        dashboard.config['host'] = args.host
    if args.port:
        dashboard.config['port'] = args.port
    if args.debug:
        dashboard.config['debug'] = True
    
    # Run dashboard
    dashboard.run()


if __name__ == "__main__":
    main()
