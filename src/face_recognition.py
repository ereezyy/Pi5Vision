#!/usr/bin/env python3
"""
Face recognition and alert system for Raspberry Pi 5 with Hailo AI HAT+
This module handles face recognition, database management, and alerting
for new or unknown faces.
"""

import os
import sys
import time
import argparse
import cv2
import numpy as np
import sqlite3
import threading
import queue
import logging
import json
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('face_recognition')

class FaceDatabase:
    """
    Manages the database of known faces
    """
    def __init__(self, db_path):
        """
        Initialize the face database
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        logger.info(f"Face database initialized at {db_path}")
    
    def _init_db(self):
        """Initialize the database schema"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create tables if they don't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                visit_count INTEGER DEFAULT 1,
                notes TEXT
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (person_id) REFERENCES persons (id)
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT NOT NULL,
                image_path TEXT,
                processed BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (person_id) REFERENCES persons (id)
            )
        ''')
        
        self.conn.commit()
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def add_person(self, name, embedding, image_path=None, notes=None):
        """
        Add a new person to the database
        
        Args:
            name: Person's name
            embedding: Face embedding (numpy array)
            image_path: Path to the face image (optional)
            notes: Additional notes (optional)
            
        Returns:
            Person ID
        """
        # Insert person record
        self.cursor.execute(
            "INSERT INTO persons (name, notes) VALUES (?, ?)",
            (name, notes)
        )
        person_id = self.cursor.lastrowid
        
        # Insert face embedding
        self._add_embedding(person_id, embedding, image_path)
        
        self.conn.commit()
        logger.info(f"Added new person: {name} (ID: {person_id})")
        
        return person_id
    
    def _add_embedding(self, person_id, embedding, image_path=None):
        """
        Add a face embedding for an existing person
        
        Args:
            person_id: Person ID
            embedding: Face embedding (numpy array)
            image_path: Path to the face image (optional)
        """
        # Convert embedding to binary blob
        embedding_blob = embedding.tobytes()
        
        self.cursor.execute(
            "INSERT INTO face_embeddings (person_id, embedding, image_path) VALUES (?, ?, ?)",
            (person_id, embedding_blob, image_path)
        )
    
    def update_person_seen(self, person_id):
        """
        Update the last_seen timestamp and visit_count for a person
        
        Args:
            person_id: Person ID
        """
        self.cursor.execute(
            "UPDATE persons SET last_seen = CURRENT_TIMESTAMP, visit_count = visit_count + 1 WHERE id = ?",
            (person_id,)
        )
        self.conn.commit()
    
    def get_all_embeddings(self):
        """
        Get all face embeddings from the database
        
        Returns:
            List of tuples (person_id, name, embedding)
        """
        self.cursor.execute('''
            SELECT fe.person_id, p.name, fe.embedding
            FROM face_embeddings fe
            JOIN persons p ON fe.person_id = p.id
        ''')
        
        results = []
        for person_id, name, embedding_blob in self.cursor.fetchall():
            # Convert binary blob back to numpy array
            embedding = np.frombuffer(embedding_blob, dtype=np.float32)
            results.append((person_id, name, embedding))
        
        return results
    
    def add_alert(self, alert_type, person_id=None, image_path=None):
        """
        Add a new alert to the database
        
        Args:
            alert_type: Type of alert (e.g., 'new_face', 'unknown_face')
            person_id: Person ID (optional)
            image_path: Path to the alert image (optional)
            
        Returns:
            Alert ID
        """
        self.cursor.execute(
            "INSERT INTO alerts (person_id, alert_type, image_path) VALUES (?, ?, ?)",
            (person_id, alert_type, image_path)
        )
        alert_id = self.cursor.lastrowid
        self.conn.commit()
        
        logger.info(f"Added new alert: {alert_type} (ID: {alert_id})")
        
        return alert_id
    
    def get_unprocessed_alerts(self):
        """
        Get all unprocessed alerts
        
        Returns:
            List of alert records
        """
        self.cursor.execute('''
            SELECT a.id, a.person_id, p.name, a.timestamp, a.alert_type, a.image_path
            FROM alerts a
            LEFT JOIN persons p ON a.person_id = p.id
            WHERE a.processed = FALSE
            ORDER BY a.timestamp DESC
        ''')
        
        return self.cursor.fetchall()
    
    def mark_alert_processed(self, alert_id):
        """
        Mark an alert as processed
        
        Args:
            alert_id: Alert ID
        """
        self.cursor.execute(
            "UPDATE alerts SET processed = TRUE WHERE id = ?",
            (alert_id,)
        )
        self.conn.commit()


class FaceRecognizer:
    """
    Handles face recognition using embeddings
    """
    def __init__(self, database, embedding_size=128, similarity_threshold=0.6):
        """
        Initialize the face recognizer
        
        Args:
            database: FaceDatabase instance
            embedding_size: Size of face embeddings (default: 128)
            similarity_threshold: Threshold for face similarity (default: 0.6)
        """
        self.database = database
        self.embedding_size = embedding_size
        self.similarity_threshold = similarity_threshold
        self.known_embeddings = []
        self.known_identities = []
        
        # Load known embeddings from database
        self._load_known_embeddings()
        
        logger.info(f"Face recognizer initialized with {len(self.known_embeddings)} known faces")
    
    def _load_known_embeddings(self):
        """Load known face embeddings from the database"""
        embeddings_data = self.database.get_all_embeddings()
        
        self.known_embeddings = []
        self.known_identities = []
        
        for person_id, name, embedding in embeddings_data:
            self.known_embeddings.append(embedding)
            self.known_identities.append((person_id, name))
    
    def _calculate_similarity(self, embedding1, embedding2):
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Similarity score (0-1)
        """
        # Ensure embeddings are normalized
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        # Calculate cosine similarity
        return np.dot(embedding1, embedding2)
    
    def recognize_face(self, embedding):
        """
        Recognize a face from its embedding
        
        Args:
            embedding: Face embedding
            
        Returns:
            Tuple of (person_id, name, similarity) or None if not recognized
        """
        if not self.known_embeddings:
            return None
        
        # Calculate similarity with all known embeddings
        similarities = [self._calculate_similarity(embedding, known_emb) 
                       for known_emb in self.known_embeddings]
        
        # Find the best match
        best_idx = np.argmax(similarities)
        best_similarity = similarities[best_idx]
        
        # Check if similarity is above threshold
        if best_similarity >= self.similarity_threshold:
            person_id, name = self.known_identities[best_idx]
            return (person_id, name, best_similarity)
        
        return None
    
    def add_face(self, name, embedding, image_path=None):
        """
        Add a new face to the database
        
        Args:
            name: Person's name
            embedding: Face embedding
            image_path: Path to the face image (optional)
            
        Returns:
            Person ID
        """
        # Add to database
        person_id = self.database.add_person(name, embedding, image_path)
        
        # Update in-memory cache
        self.known_embeddings.append(embedding)
        self.known_identities.append((person_id, name))
        
        return person_id


class AlertSystem:
    """
    Handles alerts for new or unknown faces
    """
    def __init__(self, database, alert_dir):
        """
        Initialize the alert system
        
        Args:
            database: FaceDatabase instance
            alert_dir: Directory to store alert images
        """
        self.database = database
        self.alert_dir = alert_dir
        
        # Create alert directory if it doesn't exist
        os.makedirs(alert_dir, exist_ok=True)
        
        # Initialize alert handlers
        self.alert_handlers = []
        
        logger.info(f"Alert system initialized with alert directory: {alert_dir}")
    
    def add_alert_handler(self, handler):
        """
        Add an alert handler
        
        Args:
            handler: Function that takes (alert_type, person_id, name, image_path)
        """
        self.alert_handlers.append(handler)
    
    def trigger_alert(self, alert_type, person_id=None, name=None, frame=None):
        """
        Trigger an alert
        
        Args:
            alert_type: Type of alert (e.g., 'new_face', 'unknown_face')
            person_id: Person ID (optional)
            name: Person's name (optional)
            frame: Image frame (optional)
            
        Returns:
            Alert ID
        """
        # Save alert image if frame is provided
        image_path = None
        if frame is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(self.alert_dir, f"{alert_type}_{timestamp}.jpg")
            cv2.imwrite(image_path, frame)
        
        # Add alert to database
        alert_id = self.database.add_alert(alert_type, person_id, image_path)
        
        # Call alert handlers
        for handler in self.alert_handlers:
            handler(alert_type, person_id, name, image_path)
        
        return alert_id
    
    def console_alert_handler(self, alert_type, person_id, name, image_path):
        """
        Default alert handler that logs to console
        
        Args:
            alert_type: Type of alert
            person_id: Person ID
            name: Person's name
            image_path: Path to the alert image
        """
        if alert_type == 'new_face':
            logger.info(f"NEW FACE ALERT: {name} (ID: {person_id})")
        elif alert_type == 'unknown_face':
            logger.info(f"UNKNOWN FACE ALERT")
        else:
            logger.info(f"ALERT: {alert_type}")
        
        if image_path:
            logger.info(f"Alert image saved to: {image_path}")


class FaceProcessor:
    """
    Process detected faces for recognition and alerting
    """
    def __init__(self, database_path, alert_dir, faces_dir):
        """
        Initialize the face processor
        
        Args:
            database_path: Path to the face database
            alert_dir: Directory to store alert images
            faces_dir: Directory to store face images
        """
        # Create directories if they don't exist
        os.makedirs(alert_dir, exist_ok=True)
        os.makedirs(faces_dir, exist_ok=True)
        
        # Initialize components
        self.database = FaceDatabase(database_path)
        self.recognizer = FaceRecognizer(self.database)
        self.alert_system = AlertSystem(self.database, alert_dir)
        
        # Add default alert handler
        self.alert_system.add_alert_handler(self.alert_system.console_alert_handler)
        
        # Set up face tracking
        self.faces_dir = faces_dir
        self.tracked_faces = {}  # face_id -> (person_id, last_seen_time)
        self.next_unknown_id = 1
        
        logger.info("Face processor initialized")
    
    def close(self):
        """Clean up resources"""
        self.database.close()
    
    def process_detections(self, frame, detections, generate_embedding_func):
        """
        Process face detections
        
        Args:
            frame: Video frame
            detections: List of face detections (x, y, w, h, confidence)
            generate_embedding_func: Function to generate face embedding from face image
            
        Returns:
            List of processed detections with recognition results
        """
        results = []
        current_time = time.time()
        
        for x, y, w, h, confidence in detections:
            # Extract face region
            face_img = frame[y:y+h, x:x+w]
            
            # Generate face embedding
            embedding = generate_embedding_func(face_img)
            
            # Recognize face
            recognition = self.recognizer.recognize_face(embedding)
            
            if recognition:
                # Known face
                person_id, name, similarity = recognition
                
                # Update last seen time
                self.database.update_person_seen(person_id)
                
                # Track face
                face_id = f"person_{person_id}"
                self.tracked_faces[face_id] = (person_id, current_time)
                
                results.append({
                    'x': x, 'y': y, 'w': w, 'h': h,
                    'confidence': confidence,
                    'recognized': True,
                    'person_id': person_id,
                    'name': name,
                    'similarity': similarity
                })
            else:
                # Unknown face
                # Check if this face matches a recently tracked unknown face
                matched_unknown = False
                for face_id, (unknown_id, last_seen) in list(self.tracked_faces.items()):
                    if face_id.startswith('unknown_') and current_time - last_seen < 5.0:
                        # Consider this the same unknown person if seen within 5 seconds
                        matched_unknown = True
                        self.tracked_faces[face_id] = (unknown_id, current_time)
                        unknown_name = f"Unknown_{unknown_id}"
                        
                        results.append({
                            'x': x, 'y': y, 'w': w, 'h': h,
                            'confidence': confidence,
                            'recognized': False,
                            'unknown_id': unknown_id,
                            'name': unknown_name
                        })
                        
                        # Trigger alert for unknown face (but not too frequently)
                        if current_time - last_seen > 30.0:  # Alert every 30 seconds for same unknown face
                            self.alert_system.trigger_alert('unknown_face', frame=frame)
                        
                        break
                
                if not matched_unknown:
                    # New unknown face
                    unknown_id = self.next_unknown_id
                    self.next_unknown_id += 1
                    
                    face_id = f"unknown_{unknown_id}"
                    self.tracked_faces[face_id] = (unknown_id, current_time)
                    unknown_name = f"Unknown_{unknown_id}"
                    
                    results.append({
                        'x': x, 'y': y, 'w': w, 'h': h,
                        'confidence': confidence,
                        'recognized': False,
                        'unknown_id': unknown_id,
                        'name': unknown_name
                    })
                    
                    # Save face image
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    face_path = os.path.join(self.faces_dir, f"unknown_{unknown_id}_{timestamp}.jpg")
                    cv2.imwrite(face_path, face_img)
                    
                    # Trigger alert for new unknown face
                    self.alert_system.trigger_alert('unknown_face', frame=frame)
        
        # Clean up old tracked faces
        for face_id in list(self.tracked_faces.keys()):
            if current_time - self.tracked_faces[face_id][1] > 60.0:  # Remove after 60 seconds of not seeing
                del self.tracked_faces[face_id]
        
        return results
    
    def add_new_face(self, name, face_img):
        """
        Add a new face to the database
        
        Args:
            name: Person's name
            face_img: Face image
            
        Returns:
            Person ID
        """
        # Generate embedding
        embedding = self._generate_embedding(face_img)
        
        # Save face image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = os.path.join(self.faces_dir, f"{name}_{timestamp}.jpg")
        cv2.imwrite(image_path, face_img)
        
        # Add to database
        person_id = self.recognizer.add_face(name, embedding, image_path)
        
        # Trigger alert for new face
        self.alert_system.trigger_alert('new_face', person_id, name, face_img)
        
        return person_id
    
    def _generate_embedding(self, face_img):
        """
        Generate face embedding (placeholder for actual implementation)
        
        Args:
            face_img: Face image
            
        Returns:
            Face embedding (numpy array)
        """
        # This is a placeholder - in the actual implementation,
        # we would use a face embedding model
        # For demonstration, we'll generate a random embedding
        return np.random.rand(128).astype(np.float32)


def simulate_embedding_generation(face_img):
    """
    Simulate face embedding generation (placeholder for actual model)
    
    Args:
        face_img: Face image
        
    Returns:
        Face embedding (numpy array)
    """
    # This is a placeholder - in the actual implementation,
    # we would use a face embedding model
    # For demonstration, we'll generate a random embedding
    return np.random.rand(128).astype(np.float32)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Face Recognition and Alert System")
    parser.add_argument("--db", type=str, default="faces.db", help="Path to face database")
    parser.add_argument("--alert-dir", type=str, default="alerts", help="Directory to store alert images")
    parser.add_argument("--faces-dir", type=str, default="faces", help="Directory to store face images")
    args = parser.parse_args()
    
    # Ensure paths are absolute
    db_path = os.path.abspath(args.db)
    alert_dir = os.path.abspath(args.alert_dir)
    faces_dir = os.path.abspath(args.faces_dir)
    
    logger.info(f"Starting face recognition with database {db_path}")
    
    try:
        # Initialize face processor
        processor = FaceProcessor(db_path, alert_dir, faces_dir)
        
        # Simulate processing some detections
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = [(100, 100, 200, 200, 0.95)]
        
        results = processor.process_detections(frame, detections, simulate_embedding_generation)
        
        logger.info(f"Processed {len(results)} detections")
        logger.info(f"Results: {json.dumps(results, indent=2)}")
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
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
