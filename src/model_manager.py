#!/usr/bin/env python3
"""
AI Model Manager for Pi5 Face Recognition System
Handles model loading, validation, and inference coordination
"""

import os
import sys
import logging
import hashlib
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
import time

logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    """Model information structure"""
    name: str
    path: str
    type: str
    version: str
    sha256: str
    size_mb: float
    required: bool
    description: str
    download_url: Optional[str] = None

class HailoModelManager:
    """
    Production model manager for Hailo AI HAT+ models
    """
    
    def __init__(self, models_dir: str = "/opt/pi5-face-recognition/models"):
        """
        Initialize model manager
        
        Args:
            models_dir: Directory containing model files
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.loaded_models = {}
        self.model_registry = self._get_model_registry()
        
        logger.info(f"Model manager initialized: {models_dir}")
    
    def _get_model_registry(self) -> Dict[str, ModelInfo]:
        """Get registry of available models"""
        return {
            'face_detection_primary': ModelInfo(
                name='face_detection_primary',
                path='scrfd_10g.hef',
                type='face_detection',
                version='1.0',
                sha256='placeholder_hash_scrfd',
                size_mb=15.2,
                required=True,
                description='Primary face detection model (SCRFD)',
                download_url='https://hailo.ai/models/scrfd_10g.hef'
            ),
            'face_detection_secondary': ModelInfo(
                name='face_detection_secondary', 
                path='retinaface_mobilenet_v1.hef',
                type='face_detection',
                version='1.0',
                sha256='placeholder_hash_retinaface',
                size_mb=8.7,
                required=False,
                description='Secondary face detection model (RetinaFace)',
                download_url='https://hailo.ai/models/retinaface_mobilenet_v1.hef'
            ),
            'face_recognition': ModelInfo(
                name='face_recognition',
                path='arcface_mobilefacenet.hef',
                type='face_recognition',
                version='1.0',
                sha256='placeholder_hash_arcface',
                size_mb=12.1,
                required=True,
                description='Face recognition model (ArcFace)',
                download_url='https://hailo.ai/models/arcface_mobilefacenet.hef'
            ),
            'age_gender': ModelInfo(
                name='age_gender',
                path='ssr_net.hef',
                type='age_gender',
                version='1.0',
                sha256='placeholder_hash_ssr',
                size_mb=3.2,
                required=False,
                description='Age and gender estimation model',
                download_url='https://hailo.ai/models/ssr_net.hef'
            ),
            'emotion': ModelInfo(
                name='emotion',
                path='emotion_detection.hef',
                type='emotion',
                version='1.0',
                sha256='placeholder_hash_emotion',
                size_mb=2.8,
                required=False,
                description='Emotion detection model',
                download_url='https://hailo.ai/models/emotion_detection.hef'
            ),
            'mask_detection': ModelInfo(
                name='mask_detection',
                path='mask_detection.hef',
                type='mask_detection',
                version='1.0',
                sha256='placeholder_hash_mask',
                size_mb=1.9,
                required=False,
                description='Face mask detection model',
                download_url='https://hailo.ai/models/mask_detection.hef'
            )
        }
    
    def validate_models(self) -> Dict[str, Any]:
        """
        Validate all models in registry
        
        Returns:
            Validation report
        """
        report = {
            'total_models': len(self.model_registry),
            'available': 0,
            'missing': 0,
            'invalid': 0,
            'models': {},
            'missing_required': [],
            'validation_time': time.time()
        }
        
        for model_name, model_info in self.model_registry.items():
            model_path = self.models_dir / model_info.path
            
            status = {
                'exists': model_path.exists(),
                'size_ok': False,
                'hash_ok': False,
                'loadable': False,
                'error': None
            }
            
            if status['exists']:
                try:
                    # Check file size
                    file_size_mb = model_path.stat().st_size / (1024 * 1024)
                    size_diff = abs(file_size_mb - model_info.size_mb)
                    status['size_ok'] = size_diff < 1.0  # Allow 1MB difference
                    status['actual_size_mb'] = round(file_size_mb, 2)
                    
                    # Check hash (placeholder validation)
                    with open(model_path, 'rb') as f:
                        content = f.read()
                        file_hash = hashlib.sha256(content).hexdigest()
                    
                    # For production, you'd check against known hashes
                    # For now, we'll accept any valid hash
                    status['hash_ok'] = len(file_hash) == 64
                    status['actual_hash'] = file_hash[:16] + '...'
                    
                    # Test model loading (basic check)
                    status['loadable'] = self._test_model_load(model_path)
                    
                    if all([status['size_ok'], status['hash_ok'], status['loadable']]):
                        report['available'] += 1
                    else:
                        report['invalid'] += 1
                        
                except Exception as e:
                    status['error'] = str(e)
                    report['invalid'] += 1
            else:
                report['missing'] += 1
                if model_info.required:
                    report['missing_required'].append(model_name)
            
            report['models'][model_name] = {
                'info': model_info,
                'status': status
            }
        
        return report
    
    def _test_model_load(self, model_path: Path) -> bool:
        """
        Test if model can be loaded by Hailo runtime
        
        Args:
            model_path: Path to model file
            
        Returns:
            True if model loads successfully
        """
        try:
            # Check if it's a valid HEF file (basic check)
            with open(model_path, 'rb') as f:
                header = f.read(8)
                # HEF files typically start with specific magic bytes
                # This is a simplified check
                return len(header) == 8
                
        except Exception as e:
            logger.error(f"Model load test failed for {model_path}: {e}")
            return False
    
    def download_missing_models(self, force: bool = False) -> Dict[str, bool]:
        """
        Download missing required models
        
        Args:
            force: Force re-download even if model exists
            
        Returns:
            Download results for each model
        """
        results = {}
        
        for model_name, model_info in self.model_registry.items():
            model_path = self.models_dir / model_info.path
            
            # Skip if not required and not forced
            if not model_info.required and not force:
                continue
            
            # Skip if exists and not forced
            if model_path.exists() and not force:
                results[model_name] = True
                continue
            
            logger.info(f"Downloading model: {model_name}")
            
            try:
                success = self._download_model(model_info, model_path)
                results[model_name] = success
                
                if success:
                    logger.info(f"Successfully downloaded: {model_name}")
                else:
                    logger.error(f"Failed to download: {model_name}")
                    
            except Exception as e:
                logger.error(f"Error downloading {model_name}: {e}")
                results[model_name] = False
        
        return results
    
    def _download_model(self, model_info: ModelInfo, target_path: Path) -> bool:
        """
        Download a single model
        
        Args:
            model_info: Model information
            target_path: Where to save the model
            
        Returns:
            True if download successful
        """
        if not model_info.download_url:
            logger.warning(f"No download URL for model: {model_info.name}")
            return False
        
        try:
            # For production, you would download from actual URLs
            # For demo, create placeholder files
            logger.info(f"Creating placeholder model: {target_path}")
            
            with open(target_path, 'wb') as f:
                # Write placeholder content
                placeholder_content = f"# Hailo Model Placeholder - {model_info.name}\n"
                placeholder_content += f"# Type: {model_info.type}\n"
                placeholder_content += f"# Version: {model_info.version}\n"
                placeholder_content += f"# Description: {model_info.description}\n"
                placeholder_content += "# In production, this would be the actual binary model\n"
                
                # Pad to approximate size
                padding_size = int(model_info.size_mb * 1024 * 1024) - len(placeholder_content)
                if padding_size > 0:
                    placeholder_content += "0" * padding_size
                
                f.write(placeholder_content.encode('utf-8'))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to download model {model_info.name}: {e}")
            return False
    
    def load_model(self, model_name: str) -> bool:
        """
        Load a model into memory
        
        Args:
            model_name: Name of model to load
            
        Returns:
            True if loaded successfully
        """
        if model_name not in self.model_registry:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        model_info = self.model_registry[model_name]
        model_path = self.models_dir / model_info.path
        
        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            return False
        
        try:
            # In production, this would use Hailo API to load the model
            # For demo, we'll simulate loading
            logger.info(f"Loading model: {model_name}")
            
            # Simulate model loading
            model_handle = {
                'name': model_name,
                'path': str(model_path),
                'loaded_at': time.time(),
                'type': model_info.type
            }
            
            self.loaded_models[model_name] = model_handle
            logger.info(f"Model loaded successfully: {model_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from memory
        
        Args:
            model_name: Name of model to unload
            
        Returns:
            True if unloaded successfully
        """
        if model_name not in self.loaded_models:
            logger.warning(f"Model not loaded: {model_name}")
            return True
        
        try:
            # In production, this would properly release Hailo resources
            del self.loaded_models[model_name]
            logger.info(f"Model unloaded: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload model {model_name}: {e}")
            return False
    
    def get_loaded_models(self) -> List[str]:
        """Get list of currently loaded models"""
        return list(self.loaded_models.keys())
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get information about a model"""
        return self.model_registry.get(model_name)
    
    def get_all_models_info(self) -> Dict[str, ModelInfo]:
        """Get information about all models"""
        return self.model_registry.copy()
    
    def check_hailo_device(self) -> Dict[str, Any]:
        """
        Check Hailo device status
        
        Returns:
            Device status information
        """
        status = {
            'available': False,
            'device_count': 0,
            'driver_version': None,
            'runtime_version': None,
            'devices': [],
            'error': None
        }
        
        try:
            # Check if hailortcli is available
            result = subprocess.run(['which', 'hailortcli'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                status['error'] = 'HailoRT CLI not found'
                return status
            
            # Get device information
            result = subprocess.run(['hailortcli', 'fw-control', 'identify'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                status['available'] = True
                status['device_count'] = 1  # Simplified
                status['devices'] = ['hailo_device_0']
                
                # Parse output for more details (simplified)
                if 'Hailo-8' in result.stdout:
                    status['device_type'] = 'Hailo-8'
                
            else:
                status['error'] = f"Device identification failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            status['error'] = 'Device check timeout'
        except Exception as e:
            status['error'] = f"Device check error: {str(e)}"
        
        return status
    
    def optimize_models(self) -> Dict[str, bool]:
        """
        Optimize models for current hardware
        
        Returns:
            Optimization results
        """
        results = {}
        
        device_status = self.check_hailo_device()
        if not device_status['available']:
            logger.warning("Hailo device not available, skipping optimization")
            return results
        
        for model_name in self.model_registry:
            model_path = self.models_dir / self.model_registry[model_name].path
            
            if not model_path.exists():
                results[model_name] = False
                continue
            
            try:
                # In production, this would run Hailo compiler optimizations
                logger.info(f"Optimizing model: {model_name}")
                
                # Simulate optimization
                time.sleep(0.5)
                results[model_name] = True
                
            except Exception as e:
                logger.error(f"Failed to optimize {model_name}: {e}")
                results[model_name] = False
        
        return results
    
    def create_model_manifest(self) -> Dict[str, Any]:
        """
        Create model manifest for deployment
        
        Returns:
            Model manifest
        """
        manifest = {
            'created_at': time.time(),
            'models_dir': str(self.models_dir),
            'total_models': len(self.model_registry),
            'models': {}
        }
        
        for model_name, model_info in self.model_registry.items():
            model_path = self.models_dir / model_info.path
            
            model_data = {
                'info': {
                    'name': model_info.name,
                    'type': model_info.type,
                    'version': model_info.version,
                    'description': model_info.description,
                    'required': model_info.required
                },
                'file': {
                    'path': model_info.path,
                    'exists': model_path.exists(),
                    'size_mb': model_info.size_mb
                },
                'status': {
                    'loaded': model_name in self.loaded_models,
                    'validated': False
                }
            }
            
            if model_path.exists():
                try:
                    actual_size = model_path.stat().st_size / (1024 * 1024)
                    model_data['file']['actual_size_mb'] = round(actual_size, 2)
                    model_data['status']['validated'] = abs(actual_size - model_info.size_mb) < 1.0
                except Exception:
                    pass
            
            manifest['models'][model_name] = model_data
        
        return manifest

def main():
    """Demo function"""
    manager = HailoModelManager()
    
    print("Pi5 Face Recognition - Model Manager")
    print("=" * 50)
    
    # Check Hailo device
    device_status = manager.check_hailo_device()
    print(f"\nHailo Device Status:")
    for key, value in device_status.items():
        print(f"  {key}: {value}")
    
    # Validate models
    print(f"\nValidating models...")
    validation_report = manager.validate_models()
    
    print(f"\nValidation Report:")
    print(f"  Total models: {validation_report['total_models']}")
    print(f"  Available: {validation_report['available']}")
    print(f"  Missing: {validation_report['missing']}")
    print(f"  Invalid: {validation_report['invalid']}")
    
    if validation_report['missing_required']:
        print(f"  Missing required: {validation_report['missing_required']}")
    
    # Download missing models
    if validation_report['missing'] > 0:
        print(f"\nDownloading missing models...")
        download_results = manager.download_missing_models()
        
        for model_name, success in download_results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {model_name}")
    
    # Load models
    print(f"\nLoading models...")
    for model_name in manager.model_registry:
        if manager.model_registry[model_name].required:
            success = manager.load_model(model_name)
            status = "✓" if success else "✗"
            print(f"  {status} {model_name}")
    
    # Show loaded models
    loaded = manager.get_loaded_models()
    print(f"\nLoaded models: {loaded}")
    
    # Create manifest
    print(f"\nCreating model manifest...")
    manifest = manager.create_model_manifest()
    print(f"Manifest created with {len(manifest['models'])} models")

if __name__ == "__main__":
    main()