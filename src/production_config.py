#!/usr/bin/env python3
"""
Production Configuration Manager for Pi5 Face Recognition System
Handles all system configuration with validation and environment detection
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class CameraConfig:
    """Camera configuration settings"""
    device_path: str = "/dev/video0"
    resolution: tuple = (1280, 720)
    fps: int = 30
    auto_exposure: bool = True
    brightness: int = 50
    contrast: int = 50

@dataclass
class HailoConfig:
    """Hailo AI accelerator configuration"""
    model_path: str = "/opt/pi5-face-recognition/models/retinaface_mobilenet_v1.hef"
    batch_size: int = 1
    device_id: int = 0
    enable_async: bool = True
    optimization_level: int = 2

@dataclass
class DetectionConfig:
    """Face detection configuration"""
    confidence_threshold: float = 0.6
    similarity_threshold: float = 0.7
    max_faces_per_frame: int = 10
    enable_tracking: bool = True
    tracking_timeout: int = 30

@dataclass
class DatabaseConfig:
    """Database configuration"""
    type: str = "postgresql"
    host: str = "localhost"
    port: int = 5432
    database: str = "face_recognition"
    username: str = "pi5user"
    password: str = "pi5pass"
    pool_size: int = 10
    backup_interval_hours: int = 24

@dataclass
class WebConfig:
    """Web interface configuration"""
    host: str = "0.0.0.0"
    port: int = 8080
    enable_ssl: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    cors_origins: List[str] = None
    session_timeout: int = 3600

@dataclass
class AlertConfig:
    """Alert system configuration"""
    enable_notifications: bool = True
    alert_on_unknown: bool = True
    alert_cooldown_seconds: int = 30
    email_enabled: bool = False
    telegram_enabled: bool = False
    mqtt_enabled: bool = False

@dataclass
class PrivacyConfig:
    """Privacy and security configuration"""
    enable_encryption: bool = True
    store_images: bool = True
    data_retention_days: int = 30
    blur_unknown_faces: bool = False
    privacy_zones: List[Dict[str, float]] = None

@dataclass
class PerformanceConfig:
    """Performance optimization configuration"""
    enable_gpu_acceleration: bool = True
    max_concurrent_streams: int = 4
    buffer_size: int = 10
    processing_threads: int = 4
    memory_limit_mb: int = 1024

class ProductionConfigManager:
    """
    Production configuration manager with environment detection and validation
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path) if config_path else Path("/opt/pi5-face-recognition/config/config.json")
        self.base_dir = Path("/opt/pi5-face-recognition")
        
        # Initialize configuration components
        self.camera = CameraConfig()
        self.hailo = HailoConfig()
        self.detection = DetectionConfig()
        self.database = DatabaseConfig()
        self.web = WebConfig()
        self.alerts = AlertConfig()
        self.privacy = PrivacyConfig()
        self.performance = PerformanceConfig()
        
        # System information
        self.system_info = self._detect_system_info()
        
        # Load configuration if file exists
        if self.config_path.exists():
            self.load_config()
        
        # Auto-detect and configure hardware
        self._auto_configure_hardware()
        
        logger.info("Production configuration manager initialized")
    
    def _detect_system_info(self) -> Dict[str, Any]:
        """
        Detect system information and capabilities
        
        Returns:
            Dictionary with system information
        """
        info = {
            'platform': 'unknown',
            'cpu_count': os.cpu_count() or 4,
            'memory_mb': 0,
            'disk_space_gb': 0,
            'cameras': [],
            'hailo_devices': [],
            'network_interfaces': [],
            'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
            'detected_at': datetime.now().isoformat()
        }
        
        # Detect platform
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().strip()
                if 'Raspberry Pi 5' in model:
                    info['platform'] = 'raspberry_pi_5'
                elif 'Raspberry Pi' in model:
                    info['platform'] = 'raspberry_pi'
                else:
                    info['platform'] = 'linux'
        except:
            info['platform'] = 'unknown'
        
        # Detect memory
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        info['memory_mb'] = int(line.split()[1]) // 1024
                        break
        except:
            pass
        
        # Detect disk space
        try:
            result = subprocess.run(['df', '-BG', '/'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    info['disk_space_gb'] = int(lines[1].split()[1].rstrip('G'))
        except:
            pass
        
        # Detect cameras
        try:
            cameras = []
            for i in range(10):  # Check up to 10 video devices
                device_path = f"/dev/video{i}"
                if os.path.exists(device_path):
                    cameras.append({
                        'device': device_path,
                        'index': i,
                        'available': True
                    })
            info['cameras'] = cameras
        except:
            pass
        
        # Detect Hailo devices
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True)
            if result.returncode == 0:
                hailo_devices = []
                for line in result.stdout.split('\n'):
                    if 'hailo' in line.lower():
                        hailo_devices.append(line.strip())
                info['hailo_devices'] = hailo_devices
        except:
            pass
        
        # Detect network interfaces
        try:
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
            if result.returncode == 0:
                interfaces = []
                for line in result.stdout.split('\n'):
                    if 'inet ' in line and '127.0.0.1' not in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            ip = parts[1].split('/')[0]
                            interfaces.append(ip)
                info['network_interfaces'] = interfaces
        except:
            pass
        
        return info
    
    def _auto_configure_hardware(self):
        """Auto-configure hardware settings based on detected capabilities"""
        
        # Configure camera
        if self.system_info['cameras']:
            self.camera.device_path = self.system_info['cameras'][0]['device']
            logger.info(f"Auto-configured camera: {self.camera.device_path}")
        
        # Configure performance based on system capabilities
        cpu_count = self.system_info['cpu_count']
        memory_mb = self.system_info['memory_mb']
        
        # Adjust processing threads based on CPU count
        self.performance.processing_threads = max(2, cpu_count - 1)
        
        # Adjust memory limits based on available memory
        if memory_mb > 0:
            # Use up to 25% of available memory for face recognition
            self.performance.memory_limit_mb = min(1024, memory_mb // 4)
        
        # Configure concurrent streams based on system capabilities
        if memory_mb >= 8192:  # 8GB+
            self.performance.max_concurrent_streams = 4
        elif memory_mb >= 4096:  # 4GB+
            self.performance.max_concurrent_streams = 2
        else:
            self.performance.max_concurrent_streams = 1
        
        # Configure Hailo settings
        if self.system_info['hailo_devices']:
            self.hailo.enable_async = True
            logger.info("Auto-configured Hailo AI acceleration")
        else:
            self.hailo.enable_async = False
            logger.warning("Hailo device not detected, falling back to CPU processing")
        
        # Configure web interface
        if self.system_info['network_interfaces']:
            # Use first non-localhost IP for web interface
            self.web.host = "0.0.0.0"  # Listen on all interfaces
            logger.info(f"Web interface will be available at: http://{self.system_info['network_interfaces'][0]}:{self.web.port}")
    
    def load_config(self) -> bool:
        """
        Load configuration from file
        
        Returns:
            True if configuration was loaded successfully
        """
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            # Update configuration objects
            if 'camera' in config_data:
                self._update_dataclass(self.camera, config_data['camera'])
            
            if 'hailo' in config_data:
                self._update_dataclass(self.hailo, config_data['hailo'])
            
            if 'detection' in config_data:
                self._update_dataclass(self.detection, config_data['detection'])
            
            if 'database' in config_data:
                self._update_dataclass(self.database, config_data['database'])
            
            if 'web' in config_data:
                self._update_dataclass(self.web, config_data['web'])
            
            if 'alerts' in config_data:
                self._update_dataclass(self.alerts, config_data['alerts'])
            
            if 'privacy' in config_data:
                self._update_dataclass(self.privacy, config_data['privacy'])
            
            if 'performance' in config_data:
                self._update_dataclass(self.performance, config_data['performance'])
            
            logger.info(f"Configuration loaded from {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        Save current configuration to file
        
        Returns:
            True if configuration was saved successfully
        """
        try:
            # Ensure config directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create configuration dictionary
            config_data = {
                'system_info': self.system_info,
                'camera': asdict(self.camera),
                'hailo': asdict(self.hailo),
                'detection': asdict(self.detection),
                'database': asdict(self.database),
                'web': asdict(self.web),
                'alerts': asdict(self.alerts),
                'privacy': asdict(self.privacy),
                'performance': asdict(self.performance),
                'last_updated': datetime.now().isoformat()
            }
            
            # Save to file
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def _update_dataclass(self, dataclass_obj, updates: Dict[str, Any]):
        """Update dataclass object with dictionary values"""
        for key, value in updates.items():
            if hasattr(dataclass_obj, key):
                setattr(dataclass_obj, key, value)
    
    def validate_config(self) -> List[str]:
        """
        Validate current configuration
        
        Returns:
            List of validation errors (empty if no errors)
        """
        errors = []
        
        # Validate camera configuration
        if not os.path.exists(self.camera.device_path):
            errors.append(f"Camera device not found: {self.camera.device_path}")
        
        if not (480 <= self.camera.resolution[0] <= 4096):
            errors.append(f"Invalid camera width: {self.camera.resolution[0]}")
        
        if not (480 <= self.camera.resolution[1] <= 4096):
            errors.append(f"Invalid camera height: {self.camera.resolution[1]}")
        
        if not (1 <= self.camera.fps <= 60):
            errors.append(f"Invalid camera FPS: {self.camera.fps}")
        
        # Validate Hailo configuration
        if not os.path.exists(self.hailo.model_path):
            errors.append(f"Hailo model not found: {self.hailo.model_path}")
        
        # Validate detection thresholds
        if not (0.0 <= self.detection.confidence_threshold <= 1.0):
            errors.append(f"Invalid confidence threshold: {self.detection.confidence_threshold}")
        
        if not (0.0 <= self.detection.similarity_threshold <= 1.0):
            errors.append(f"Invalid similarity threshold: {self.detection.similarity_threshold}")
        
        # Validate web configuration
        if not (1 <= self.web.port <= 65535):
            errors.append(f"Invalid web port: {self.web.port}")
        
        # Validate SSL configuration
        if self.web.enable_ssl:
            if not self.web.ssl_cert_path or not os.path.exists(self.web.ssl_cert_path):
                errors.append(f"SSL certificate not found: {self.web.ssl_cert_path}")
            
            if not self.web.ssl_key_path or not os.path.exists(self.web.ssl_key_path):
                errors.append(f"SSL key not found: {self.web.ssl_key_path}")
        
        # Validate performance settings
        if self.performance.processing_threads < 1:
            errors.append(f"Invalid processing threads: {self.performance.processing_threads}")
        
        if self.performance.memory_limit_mb < 256:
            errors.append(f"Memory limit too low: {self.performance.memory_limit_mb}MB")
        
        return errors
    
    def get_database_url(self) -> str:
        """
        Get database connection URL
        
        Returns:
            Database connection URL
        """
        if self.database.type == "postgresql":
            return f"postgresql://{self.database.username}:{self.database.password}@{self.database.host}:{self.database.port}/{self.database.database}"
        elif self.database.type == "sqlite":
            return f"sqlite:///{self.base_dir}/database/faces.db"
        else:
            raise ValueError(f"Unsupported database type: {self.database.type}")
    
    def get_model_paths(self) -> Dict[str, str]:
        """
        Get paths to all AI models
        
        Returns:
            Dictionary mapping model names to file paths
        """
        models_dir = self.base_dir / "models"
        
        return {
            'face_detection_primary': str(models_dir / "scrfd_10g.hef"),
            'face_detection_secondary': str(models_dir / "retinaface_mobilenet_v1.hef"),
            'face_recognition': str(models_dir / "arcface_mobilefacenet.hef"),
            'age_gender': str(models_dir / "ssr_net.hef"),
            'emotion': str(models_dir / "emotion_detection.hef"),
            'mask_detection': str(models_dir / "mask_detection.hef"),
            'anti_spoofing': str(models_dir / "anti_spoofing.hef")
        }
    
    def export_config(self) -> Dict[str, Any]:
        """
        Export complete configuration as dictionary
        
        Returns:
            Complete configuration dictionary
        """
        return {
            'system_info': self.system_info,
            'camera': asdict(self.camera),
            'hailo': asdict(self.hailo),
            'detection': asdict(self.detection),
            'database': asdict(self.database),
            'web': asdict(self.web),
            'alerts': asdict(self.alerts),
            'privacy': asdict(self.privacy),
            'performance': asdict(self.performance)
        }
    
    def get_system_requirements(self) -> Dict[str, Any]:
        """
        Get system requirements and recommendations
        
        Returns:
            System requirements information
        """
        return {
            'minimum_requirements': {
                'platform': 'Raspberry Pi 4 or 5',
                'memory_mb': 4096,
                'storage_gb': 32,
                'python_version': '3.9+',
                'camera': 'USB camera or Pi Camera'
            },
            'recommended_requirements': {
                'platform': 'Raspberry Pi 5',
                'memory_mb': 8192,
                'storage_gb': 64,
                'python_version': '3.11+',
                'camera': '1080p USB camera',
                'accelerator': 'Hailo AI HAT+ (26 TOPS)'
            },
            'current_system': {
                'platform': self.system_info['platform'],
                'memory_mb': self.system_info['memory_mb'],
                'cpu_count': self.system_info['cpu_count'],
                'cameras': len(self.system_info['cameras']),
                'hailo_devices': len(self.system_info['hailo_devices'])
            }
        }

def main():
    """Demo function for configuration manager"""
    config = ProductionConfigManager()
    
    print("Pi5 Face Recognition - Production Configuration")
    print("=" * 50)
    
    # Show system information
    print("\nSystem Information:")
    for key, value in config.system_info.items():
        print(f"  {key}: {value}")
    
    # Validate configuration
    print("\nConfiguration Validation:")
    errors = config.validate_config()
    if errors:
        print("  Errors found:")
        for error in errors:
            print(f"    - {error}")
    else:
        print("  ✓ Configuration is valid")
    
    # Show requirements
    print("\nSystem Requirements:")
    requirements = config.get_system_requirements()
    for category, reqs in requirements.items():
        print(f"  {category}:")
        for key, value in reqs.items():
            print(f"    {key}: {value}")
    
    # Save configuration
    config.save_config()
    print(f"\nConfiguration saved to: {config.config_path}")

if __name__ == "__main__":
    main()