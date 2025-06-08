#!/usr/bin/env python3
"""
Performance and Security Optimization for Raspberry Pi 5 Face Recognition System with Hailo AI HAT+
This module provides optimizations for resource usage, latency, and security
"""

import os
import sys
import time
import logging
import json
import threading
import asyncio
import hashlib
import base64
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('performance_security')

# Define Path class for WebContainer compatibility
class Path:
    def __init__(self, path):
        self.path = str(path)
    
    def __str__(self):
        return self.path
    
    def __truediv__(self, other):
        return Path(os.path.join(self.path, str(other)))

class PerformanceOptimizer:
    """
    Optimizes performance for the face recognition system
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the performance optimizer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.metrics = {
            'frame_processing_times': [],
            'detection_times': [],
            'recognition_times': [],
            'database_query_times': [],
            'total_memory_usage': [],
            'hailo_usage': [],
            'cpu_usage': []
        }
        self.optimization_status = {
            'adaptive_resolution': False,
            'frame_skipping': False,
            'batch_processing': False,
            'model_quantization': False,
            'thread_pool_optimization': False
        }
        
        # Initialize optimization parameters
        self.resolution_scale = 1.0
        self.frame_skip_ratio = 0
        self.batch_size = 1
        self.thread_pool_size = os.cpu_count() or 4
        
        # Create thread pool
        self.thread_pool = ThreadPoolManager(self.thread_pool_size)
        
        logger.info("Performance optimizer initialized")
    
    def update_metrics(self, metric_name: str, value: float):
        """
        Update performance metrics
        
        Args:
            metric_name: Name of the metric to update
            value: Value to add
        """
        if metric_name in self.metrics:
            self.metrics[metric_name].append(value)
            
            # Keep only the last 100 values
            if len(self.metrics[metric_name]) > 100:
                self.metrics[metric_name] = self.metrics[metric_name][-100:]
    
    def get_average_metric(self, metric_name: str) -> float:
        """
        Get the average value of a metric
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Average value of the metric
        """
        if metric_name in self.metrics and self.metrics[metric_name]:
            return sum(self.metrics[metric_name]) / len(self.metrics[metric_name])
        return 0.0
    
    def optimize_resolution(self, frame_time: float) -> float:
        """
        Optimize resolution based on frame processing time
        
        Args:
            frame_time: Time taken to process a frame (seconds)
            
        Returns:
            Optimized resolution scale factor
        """
        target_frame_time = 1.0 / self.config.get('target_fps', 30)
        
        # If frame time is too high, reduce resolution
        if frame_time > target_frame_time * 1.2:
            self.resolution_scale = max(0.5, self.resolution_scale - 0.05)
            self.optimization_status['adaptive_resolution'] = True
        # If frame time is low enough, increase resolution
        elif frame_time < target_frame_time * 0.8 and self.resolution_scale < 1.0:
            self.resolution_scale = min(1.0, self.resolution_scale + 0.05)
            self.optimization_status['adaptive_resolution'] = True
        
        return self.resolution_scale
    
    def optimize_frame_skipping(self, system_load: float) -> int:
        """
        Optimize frame skipping based on system load
        
        Args:
            system_load: System load factor (0.0-1.0)
            
        Returns:
            Number of frames to skip
        """
        # If system load is high, skip more frames
        if system_load > 0.8:
            self.frame_skip_ratio = 2
            self.optimization_status['frame_skipping'] = True
        elif system_load > 0.6:
            self.frame_skip_ratio = 1
            self.optimization_status['frame_skipping'] = True
        else:
            self.frame_skip_ratio = 0
            self.optimization_status['frame_skipping'] = False
        
        return self.frame_skip_ratio
    
    def optimize_batch_size(self, num_faces: int) -> int:
        """
        Optimize batch size for face recognition
        
        Args:
            num_faces: Number of faces detected
            
        Returns:
            Optimized batch size
        """
        # If many faces are detected, use batch processing
        if num_faces > 3:
            self.batch_size = min(num_faces, 8)
            self.optimization_status['batch_processing'] = True
        else:
            self.batch_size = 1
            self.optimization_status['batch_processing'] = False
        
        return self.batch_size
    
    def optimize_thread_pool(self, system_load: float) -> int:
        """
        Optimize thread pool size based on system load
        
        Args:
            system_load: System load factor (0.0-1.0)
            
        Returns:
            Optimized thread pool size
        """
        max_threads = os.cpu_count() or 4
        
        # If system load is high, reduce thread pool size
        if system_load > 0.8:
            new_size = max(2, int(max_threads * 0.5))
        elif system_load > 0.6:
            new_size = max(2, int(max_threads * 0.75))
        else:
            new_size = max_threads
        
        # Update thread pool if size changed
        if new_size != self.thread_pool_size:
            self.thread_pool_size = new_size
            self.thread_pool.resize(new_size)
            self.optimization_status['thread_pool_optimization'] = True
        
        return self.thread_pool_size
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Get the current optimization status
        
        Returns:
            Dictionary with optimization status
        """
        return {
            'status': self.optimization_status,
            'resolution_scale': self.resolution_scale,
            'frame_skip_ratio': self.frame_skip_ratio,
            'batch_size': self.batch_size,
            'thread_pool_size': self.thread_pool_size,
            'metrics': {
                'avg_frame_time': self.get_average_metric('frame_processing_times'),
                'avg_detection_time': self.get_average_metric('detection_times'),
                'avg_recognition_time': self.get_average_metric('recognition_times'),
                'avg_database_query_time': self.get_average_metric('database_query_times'),
                'avg_memory_usage': self.get_average_metric('total_memory_usage'),
                'avg_hailo_usage': self.get_average_metric('hailo_usage'),
                'avg_cpu_usage': self.get_average_metric('cpu_usage')
            }
        }
    
    def submit_task(self, func, *args, **kwargs):
        """
        Submit a task to the thread pool
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Future object
        """
        return self.thread_pool.submit(func, *args, **kwargs)


class ThreadPoolManager:
    """
    Manages a thread pool for parallel processing
    """
    def __init__(self, max_workers: int):
        """
        Initialize the thread pool manager
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers
        self.pool = None
        self.create_pool()
    
    def create_pool(self):
        """Create the thread pool"""
        from concurrent.futures import ThreadPoolExecutor
        self.pool = ThreadPoolExecutor(max_workers=self.max_workers)
    
    def resize(self, max_workers: int):
        """
        Resize the thread pool
        
        Args:
            max_workers: New maximum number of worker threads
        """
        if max_workers != self.max_workers:
            self.max_workers = max_workers
            
            # Shutdown existing pool and create a new one
            if self.pool:
                self.pool.shutdown(wait=False)
            
            self.create_pool()
    
    def submit(self, func, *args, **kwargs):
        """
        Submit a task to the thread pool
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Future object
        """
        if self.pool:
            return self.pool.submit(func, *args, **kwargs)
        return None
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        if self.pool:
            self.pool.shutdown(wait=wait)
            self.pool = None


class SecurityManager:
    """
    Manages security features for the face recognition system
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the security manager
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.base_dir = Path(config.get('base_dir', '/opt/pi5-face-recognition'))
        self.keys_dir = os.path.join(str(self.base_dir), 'keys')
        self.users_file = os.path.join(str(self.base_dir), 'config', 'users.json')
        self.session_tokens = {}
        
        # Ensure directories exist
        os.makedirs(self.keys_dir, exist_ok=True)
        os.makedirs(self.users_file.parent, exist_ok=True)
        
        # Initialize security features
        self.enable_encryption = config.get('enable_encryption', True)
        self.enable_authentication = config.get('enable_authentication', True)
        self.session_timeout = config.get('session_timeout', 3600)  # 1 hour
        
        # Load or create encryption keys
        self.encryption_key = self._load_or_create_encryption_key()
        
        # Load or create users
        self.users = self._load_or_create_users()
        
        logger.info("Security manager initialized")
    
    def _load_or_create_encryption_key(self) -> bytes:
        """
        Load or create encryption key
        
        Returns:
            Encryption key
        """
        key_file = os.path.join(self.keys_dir, 'encryption.key')
        
        if os.path.exists(key_file):
            # Load existing key
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            # Create new key
            key = secrets.token_bytes(32)  # 256-bit key
            
            # Save key
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Note: File permissions not set in WebContainer environment
        
        return key
    
    def _load_or_create_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Load or create users
        
        Returns:
            Dictionary of users
        """
        if os.path.exists(self.users_file):
            # Load existing users
            try:
                with open(self.users_file, 'r') as f:
                    users = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load users: {e}")
                users = {}
        else:
            # Create default admin user
            salt = secrets.token_hex(16)
            password_hash = self._hash_password('admin', salt)
            
            users = {
                'admin': {
                    'username': 'admin',
                    'password_hash': password_hash,
                    'salt': salt,
                    'role': 'admin',
                    'created_at': datetime.now().isoformat(),
                    'last_login': None
                }
            }
            
            # Save users
            self._save_users(users)
        
        return users
    
    def _save_users(self, users: Dict[str, Dict[str, Any]]):
        """
        Save users to file
        
        Args:
            users: Dictionary of users
        """
        try:
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
            
            # Note: File permissions not set in WebContainer environment
        except Exception as e:
            logger.error(f"Failed to save users: {e}")
    
    def _hash_password(self, password: str, salt: str) -> str:
        """
        Hash a password with salt
        
        Args:
            password: Password to hash
            salt: Salt to use
            
        Returns:
            Hashed password
        """
        # Use PBKDF2 with SHA-256
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # Number of iterations
        )
        
        return base64.b64encode(key).decode('utf-8')
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate a user
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Session token if authentication successful, None otherwise
        """
        if not self.enable_authentication:
            # Authentication disabled, generate token anyway
            token = secrets.token_hex(32)
            self.session_tokens[token] = {
                'username': 'guest',
                'role': 'guest',
                'created_at': datetime.now()
            }
            return token
        
        # Check if user exists
        if username not in self.users:
            logger.warning(f"Authentication failed: User {username} not found")
            return None
        
        # Get user
        user = self.users[username]
        
        # Check password
        salt = user['salt']
        password_hash = self._hash_password(password, salt)
        
        if password_hash != user['password_hash']:
            logger.warning(f"Authentication failed: Invalid password for user {username}")
            return None
        
        # Generate session token
        token = secrets.token_hex(32)
        
        # Store session
        self.session_tokens[token] = {
            'username': username,
            'role': user['role'],
            'created_at': datetime.now()
        }
        
        # Update last login
        user['last_login'] = datetime.now().isoformat()
        self._save_users(self.users)
        
        logger.info(f"User {username} authenticated successfully")
        return token
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session token
        
        Args:
            token: Session token
            
        Returns:
            Session information if token is valid, None otherwise
        """
        if not self.enable_authentication:
            # Authentication disabled, return guest session
            return {
                'username': 'guest',
                'role': 'guest',
                'created_at': datetime.now()
            }
        
        # Check if token exists
        if token not in self.session_tokens:
            return None
        
        # Get session
        session = self.session_tokens[token]
        
        # Check if session has expired
        created_at = session['created_at']
        if (datetime.now() - created_at).total_seconds() > self.session_timeout:
            # Session expired, remove it
            del self.session_tokens[token]
            return None
        
        return session
    
    def invalidate_token(self, token: str):
        """
        Invalidate a session token
        
        Args:
            token: Session token
        """
        if token in self.session_tokens:
            del self.session_tokens[token]
    
    def add_user(self, username: str, password: str, role: str = 'user') -> bool:
        """
        Add a new user
        
        Args:
            username: Username
            password: Password
            role: User role
            
        Returns:
            True if user was added, False otherwise
        """
        # Check if user already exists
        if username in self.users:
            logger.warning(f"Failed to add user: User {username} already exists")
            return False
        
        # Generate salt and hash password
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        
        # Create user
        self.users[username] = {
            'username': username,
            'password_hash': password_hash,
            'salt': salt,
            'role': role,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        
        # Save users
        self._save_users(self.users)
        
        logger.info(f"User {username} added successfully")
        return True
    
    def remove_user(self, username: str) -> bool:
        """
        Remove a user
        
        Args:
            username: Username
            
        Returns:
            True if user was removed, False otherwise
        """
        # Check if user exists
        if username not in self.users:
            logger.warning(f"Failed to remove user: User {username} not found")
            return False
        
        # Check if user is the last admin
        if self.users[username]['role'] == 'admin':
            admin_count = sum(1 for user in self.users.values() if user['role'] == 'admin')
            if admin_count <= 1:
                logger.warning("Failed to remove user: Cannot remove the last admin user")
                return False
        
        # Remove user
        del self.users[username]
        
        # Save users
        self._save_users(self.users)
        
        logger.info(f"User {username} removed successfully")
        return True
    
    def change_password(self, username: str, new_password: str) -> bool:
        """
        Change a user's password
        
        Args:
            username: Username
            new_password: New password
            
        Returns:
            True if password was changed, False otherwise
        """
        # Check if user exists
        if username not in self.users:
            logger.warning(f"Failed to change password: User {username} not found")
            return False
        
        # Get user
        user = self.users[username]
        
        # Generate new salt and hash password
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(new_password, salt)
        
        # Update user
        user['password_hash'] = password_hash
        user['salt'] = salt
        
        # Save users
        self._save_users(self.users)
        
        logger.info(f"Password for user {username} changed successfully")
        return True
    
    def encrypt_data(self, data: bytes) -> bytes:
        """
        Encrypt data
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data
        """
        if not self.enable_encryption:
            return data
        
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            
            # Generate IV
            iv = secrets.token_bytes(16)
            
            # Create cipher
            cipher = Cipher(algorithms.AES(self.encryption_key), modes.CBC(iv))
            encryptor = cipher.encryptor()
            
            # Pad data
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data) + padder.finalize()
            
            # Encrypt data
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Combine IV and encrypted data
            return iv + encrypted_data
        
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            return data
    
    def decrypt_data(self, data: bytes) -> bytes:
        """
        Decrypt data
        
        Args:
            data: Data to decrypt
            
        Returns:
            Decrypted data
        """
        if not self.enable_encryption:
            return data
        
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives import padding
            
            # Extract IV and encrypted data
            iv = data[:16]
            encrypted_data = data[16:]
            
            # Create cipher
            cipher = Cipher(algorithms.AES(self.encryption_key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            
            # Decrypt data
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Unpad data
            unpadder = padding.PKCS7(128).unpadder()
            return unpadder.update(padded_data) + unpadder.finalize()
        
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            return data
    
    def get_security_status(self) -> Dict[str, Any]:
        """
        Get the current security status
        
        Returns:
            Dictionary with security status
        """
        return {
            'encryption_enabled': self.enable_encryption,
            'authentication_enabled': self.enable_authentication,
            'session_timeout': self.session_timeout,
            'active_sessions': len(self.session_tokens),
            'user_count': len(self.users),
            'admin_count': sum(1 for user in self.users.values() if user['role'] == 'admin')
        }


class PrivacyManager:
    """
    Manages privacy features for the face recognition system
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the privacy manager
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.base_dir = Path(config.get('base_dir', '/opt/pi5-face-recognition'))
        self.privacy_zones = config.get('privacy_zones', [])
        self.data_retention_days = config.get('data_retention_days', 30)
        self.blur_unknown_faces = config.get('blur_unknown_faces', False)
        self.store_only_embeddings = config.get('store_only_embeddings', False)
        self.enable_consent_management = config.get('enable_consent_management', False)
        self.consent_database = os.path.join(str(self.base_dir), 'database', 'consent.db')
        
        logger.info("Privacy manager initialized")
    
    def apply_privacy_zones(self, frame: Any, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply privacy zones to detections
        
        Args:
            frame: Video frame
            detections: List of face detections
            
        Returns:
            Filtered list of detections
        """
        if not self.privacy_zones:
            return detections
        
        filtered_detections = []
        frame_height, frame_width = frame.shape[:2]
        
        for detection in detections:
            # Get bounding box
            x, y, w, h = detection['bbox']
            
            # Check if detection is in any privacy zone
            in_privacy_zone = False
            
            for zone in self.privacy_zones:
                zone_x = int(zone['x'] * frame_width)
                zone_y = int(zone['y'] * frame_height)
                zone_w = int(zone['width'] * frame_width)
                zone_h = int(zone['height'] * frame_height)
                
                # Check if detection overlaps with privacy zone
                if (x < zone_x + zone_w and x + w > zone_x and
                    y < zone_y + zone_h and y + h > zone_y):
                    in_privacy_zone = True
                    break
            
            if not in_privacy_zone:
                filtered_detections.append(detection)
        
        return filtered_detections
    
    def apply_face_blurring(self, frame: Any, detections: List[Dict[str, Any]]) -> Any:
        """
        Apply face blurring to unknown faces
        
        Args:
            frame: Video frame
            detections: List of face detections
            
        Returns:
            Frame with blurred faces
        """
        if not self.blur_unknown_faces:
            return frame
        
        import cv2
        import numpy as np
        
        # Create a copy of the frame
        blurred_frame = frame.copy()
        
        for detection in detections:
            # Check if face is unknown
            if 'person_id' not in detection or detection['person_id'] is None:
                # Get bounding box
                x, y, w, h = detection['bbox']
                
                # Extract face region
                face_region = frame[y:y+h, x:x+w]
                
                # Apply blur
                blurred_face = cv2.GaussianBlur(face_region, (99, 99), 30)
                
                # Replace face region with blurred face
                blurred_frame[y:y+h, x:x+w] = blurred_face
        
        return blurred_frame
    
    def check_data_retention(self) -> List[str]:
        """
        Check data retention policy and return files to delete
        
        Returns:
            List of files to delete
        """
        files_to_delete = []
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=self.data_retention_days)
        
        # Check alert images
        alerts_dir = os.path.join(str(self.base_dir), 'alerts')
        if os.path.exists(alerts_dir):
            for filename in os.listdir(alerts_dir):
                if filename.endswith('.jpg'):
                    file_path = os.path.join(alerts_dir, filename)
                    # Get file modification time
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # Check if file is older than cutoff date
                    if mod_time < cutoff_date:
                        files_to_delete.append(file_path)
        
        # Check logs
        logs_dir = os.path.join(str(self.base_dir), 'logs')
        if os.path.exists(logs_dir):
            for filename in os.listdir(logs_dir):
                if '.log.' in filename:
                    file_path = os.path.join(logs_dir, filename)
                    # Get file modification time
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # Check if file is older than cutoff date
                    if mod_time < cutoff_date:
                        files_to_delete.append(file_path)
        
        return files_to_delete
    
    def enforce_data_retention(self) -> int:
        """
        Enforce data retention policy by deleting old files
        
        Returns:
            Number of files deleted
        """
        files_to_delete = self.check_data_retention()
        
        # Delete files
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                deleted_count += 1
                logger.info(f"Deleted old file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_path}: {e}")
        
        return deleted_count
    
    def record_consent(self, person_id: str, consent_given: bool, consent_type: str, notes: str = None) -> bool:
        """
        Record consent for a person
        
        Args:
            person_id: Person ID
            consent_given: Whether consent was given
            consent_type: Type of consent
            notes: Additional notes
            
        Returns:
            True if consent was recorded, False otherwise
        """
        if not self.enable_consent_management:
            return False
        
        import sqlite3
        
        try:
            # Create database if it doesn't exist
            conn = sqlite3.connect(str(self.consent_database))
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS consent (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT NOT NULL,
                    consent_type TEXT NOT NULL,
                    consent_given INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    notes TEXT
                )
            ''')
            
            # Insert consent record
            cursor.execute('''
                INSERT INTO consent (person_id, consent_type, consent_given, timestamp, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                person_id,
                consent_type,
                1 if consent_given else 0,
                datetime.now().isoformat(),
                notes
            ))
            
            # Commit changes
            conn.commit()
            
            # Close connection
            conn.close()
            
            logger.info(f"Recorded consent for person {person_id}: {consent_type} = {consent_given}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to record consent: {e}")
            return False
    
    def check_consent(self, person_id: str, consent_type: str) -> Optional[bool]:
        """
        Check if a person has given consent
        
        Args:
            person_id: Person ID
            consent_type: Type of consent
            
        Returns:
            True if consent was given, False if consent was denied, None if no consent record exists
        """
        if not self.enable_consent_management:
            return None
        
        import sqlite3
        
        try:
            # Connect to database
            conn = sqlite3.connect(str(self.consent_database))
            cursor = conn.cursor()
            
            # Query consent record
            cursor.execute('''
                SELECT consent_given FROM consent
                WHERE person_id = ? AND consent_type = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (person_id, consent_type))
            
            # Get result
            result = cursor.fetchone()
            
            # Close connection
            conn.close()
            
            if result is None:
                return None
            
            return bool(result[0])
        
        except Exception as e:
            logger.error(f"Failed to check consent: {e}")
            return None
    
    def get_privacy_status(self) -> Dict[str, Any]:
        """
        Get the current privacy status
        
        Returns:
            Dictionary with privacy status
        """
        return {
            'privacy_zones': len(self.privacy_zones),
            'data_retention_days': self.data_retention_days,
            'blur_unknown_faces': self.blur_unknown_faces,
            'store_