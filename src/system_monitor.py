#!/usr/bin/env python3
"""
System Monitor for Pi5 Face Recognition System
Real-time monitoring of system performance, hardware status, and health metrics
"""

import os
import sys
import time
import psutil
import threading
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: int
    memory_available_mb: int
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    temperature_celsius: float
    load_average: List[float]
    network_bytes_sent: int
    network_bytes_recv: int
    uptime_seconds: float

@dataclass
class ProcessMetrics:
    """Process-specific metrics"""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_rss_mb: int
    threads: int
    status: str
    create_time: float

@dataclass
class HardwareStatus:
    """Hardware component status"""
    camera_available: bool
    camera_device: str
    hailo_available: bool
    hailo_device_count: int
    usb_devices: List[str]
    gpu_available: bool
    gpio_available: bool

class SystemMonitor:
    """
    Real-time system monitoring for Pi5 Face Recognition System
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize system monitor
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.base_dir = Path("/opt/pi5-face-recognition")
        self.log_dir = self.base_dir / "logs"
        self.metrics_file = self.log_dir / "system_metrics.json"
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Monitoring state
        self.is_running = False
        self.monitor_thread = None
        self.collection_interval = 5  # seconds
        self.metrics_history = []
        self.max_history_entries = 1440  # 2 hours at 5-second intervals
        
        # System information
        self.system_info = self._get_system_info()
        self.process_name = "python"  # Main process to monitor
        
        # Hardware monitoring
        self.hardware_status = HardwareStatus(
            camera_available=False,
            camera_device="",
            hailo_available=False,
            hailo_device_count=0,
            usb_devices=[],
            gpu_available=False,
            gpio_available=False
        )
        
        # Performance thresholds
        self.thresholds = {
            'cpu_warning': 80.0,
            'cpu_critical': 95.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'temperature_warning': 75.0,
            'temperature_critical': 85.0
        }
        
        logger.info("System monitor initialized")
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get static system information"""
        try:
            # Get CPU information
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            
            # Get memory information
            memory = psutil.virtual_memory()
            
            # Get disk information
            disk = psutil.disk_usage('/')
            
            # Get network interfaces
            network_interfaces = list(psutil.net_if_addrs().keys())
            
            # Get boot time
            boot_time = psutil.boot_time()
            
            return {
                'hostname': os.uname().nodename,
                'platform': os.uname().system,
                'architecture': os.uname().machine,
                'cpu_count_physical': cpu_count,
                'cpu_count_logical': cpu_count_logical,
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'network_interfaces': network_interfaces,
                'boot_time': datetime.fromtimestamp(boot_time).isoformat(),
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}
    
    def start_monitoring(self):
        """Start system monitoring"""
        if self.is_running:
            logger.warning("System monitoring is already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        if not self.is_running:
            logger.warning("System monitoring is not running")
            return
        
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        
        logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Collect metrics
                metrics = self._collect_metrics()
                
                # Add to history
                self.metrics_history.append(metrics)
                
                # Limit history size
                if len(self.metrics_history) > self.max_history_entries:
                    self.metrics_history = self.metrics_history[-self.max_history_entries:]
                
                # Check thresholds and generate alerts
                self._check_thresholds(metrics)
                
                # Update hardware status
                self._update_hardware_status()
                
                # Save metrics to file periodically
                if len(self.metrics_history) % 12 == 0:  # Every minute
                    self._save_metrics()
                
                # Wait for next collection
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_used_mb = round((memory.total - memory.available) / (1024**2))
            memory_available_mb = round(memory.available / (1024**2))
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_used_gb = round((disk.total - disk.free) / (1024**3), 2)
            disk_free_gb = round(disk.free / (1024**3), 2)
            
            # Temperature
            temperature = self._get_temperature()
            
            # Load average
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else [0.0, 0.0, 0.0]
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Uptime
            uptime = time.time() - psutil.boot_time()
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_percent=disk.percent,
                disk_used_gb=disk_used_gb,
                disk_free_gb=disk_free_gb,
                temperature_celsius=temperature,
                load_average=list(load_avg),
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                uptime_seconds=uptime
            )
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0, memory_percent=0.0, memory_used_mb=0, memory_available_mb=0,
                disk_percent=0.0, disk_used_gb=0.0, disk_free_gb=0.0,
                temperature_celsius=0.0, load_average=[0.0, 0.0, 0.0],
                network_bytes_sent=0, network_bytes_recv=0, uptime_seconds=0.0
            )
    
    def _get_temperature(self) -> float:
        """Get CPU temperature"""
        try:
            # Try Raspberry Pi temperature file
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_str = f.read().strip()
                    return float(temp_str) / 1000.0
            
            # Try psutil sensors
            sensors = psutil.sensors_temperatures()
            if 'cpu_thermal' in sensors:
                return sensors['cpu_thermal'][0].current
            elif 'coretemp' in sensors:
                return sensors['coretemp'][0].current
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _update_hardware_status(self):
        """Update hardware status"""
        try:
            # Check camera availability
            camera_devices = []
            for i in range(10):
                device_path = f"/dev/video{i}"
                if os.path.exists(device_path):
                    camera_devices.append(device_path)
            
            self.hardware_status.camera_available = len(camera_devices) > 0
            self.hardware_status.camera_device = camera_devices[0] if camera_devices else ""
            
            # Check Hailo devices
            try:
                import subprocess
                result = subprocess.run(['lspci'], capture_output=True, text=True)
                hailo_count = result.stdout.lower().count('hailo') if result.returncode == 0 else 0
                self.hardware_status.hailo_available = hailo_count > 0
                self.hardware_status.hailo_device_count = hailo_count
            except:
                self.hardware_status.hailo_available = False
                self.hardware_status.hailo_device_count = 0
            
            # Check USB devices
            try:
                import subprocess
                result = subprocess.run(['lsusb'], capture_output=True, text=True)
                usb_devices = []
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            usb_devices.append(line.strip())
                self.hardware_status.usb_devices = usb_devices
            except:
                self.hardware_status.usb_devices = []
            
            # Check GPIO availability
            self.hardware_status.gpio_available = os.path.exists('/sys/class/gpio')
            
            # Check GPU availability (very basic check)
            self.hardware_status.gpu_available = os.path.exists('/dev/dri') or os.path.exists('/proc/device-tree/soc/gpu')
            
        except Exception as e:
            logger.error(f"Failed to update hardware status: {e}")
    
    def _check_thresholds(self, metrics: SystemMetrics):
        """Check metrics against thresholds and generate alerts"""
        alerts = []
        
        # CPU threshold checks
        if metrics.cpu_percent >= self.thresholds['cpu_critical']:
            alerts.append(f"CRITICAL: CPU usage at {metrics.cpu_percent:.1f}%")
        elif metrics.cpu_percent >= self.thresholds['cpu_warning']:
            alerts.append(f"WARNING: CPU usage at {metrics.cpu_percent:.1f}%")
        
        # Memory threshold checks
        if metrics.memory_percent >= self.thresholds['memory_critical']:
            alerts.append(f"CRITICAL: Memory usage at {metrics.memory_percent:.1f}%")
        elif metrics.memory_percent >= self.thresholds['memory_warning']:
            alerts.append(f"WARNING: Memory usage at {metrics.memory_percent:.1f}%")
        
        # Disk threshold checks
        if metrics.disk_percent >= self.thresholds['disk_critical']:
            alerts.append(f"CRITICAL: Disk usage at {metrics.disk_percent:.1f}%")
        elif metrics.disk_percent >= self.thresholds['disk_warning']:
            alerts.append(f"WARNING: Disk usage at {metrics.disk_percent:.1f}%")
        
        # Temperature threshold checks
        if metrics.temperature_celsius >= self.thresholds['temperature_critical']:
            alerts.append(f"CRITICAL: Temperature at {metrics.temperature_celsius:.1f}°C")
        elif metrics.temperature_celsius >= self.thresholds['temperature_warning']:
            alerts.append(f"WARNING: Temperature at {metrics.temperature_celsius:.1f}°C")
        
        # Log alerts
        for alert in alerts:
            logger.warning(alert)
    
    def _save_metrics(self):
        """Save metrics to file"""
        try:
            # Prepare data for saving
            data = {
                'system_info': self.system_info,
                'hardware_status': asdict(self.hardware_status),
                'thresholds': self.thresholds,
                'metrics_history': [asdict(m) for m in self.metrics_history[-100:]],  # Last 100 entries
                'last_updated': datetime.now().isoformat()
            }
            
            # Save to file
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent metrics"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None
    
    def get_metrics_history(self, minutes: int = 60) -> List[SystemMetrics]:
        """
        Get metrics history for the specified time period
        
        Args:
            minutes: Number of minutes of history to return
            
        Returns:
            List of metrics within the time period
        """
        if not self.metrics_history:
            return []
        
        # Calculate how many entries to return
        entries_needed = min(minutes * 60 // self.collection_interval, len(self.metrics_history))
        
        return self.metrics_history[-entries_needed:]
    
    def get_process_metrics(self, process_name: str = None) -> List[ProcessMetrics]:
        """
        Get metrics for specific processes
        
        Args:
            process_name: Name of process to monitor (defaults to face recognition processes)
            
        Returns:
            List of process metrics
        """
        if process_name is None:
            # Default to face recognition related processes
            process_names = ['python', 'face_tracking', 'face_recognition']
        else:
            process_names = [process_name]
        
        process_metrics = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info', 'num_threads', 'status', 'create_time']):
                try:
                    if any(name in proc.info['name'].lower() for name in process_names):
                        memory_rss_mb = round(proc.info['memory_info'].rss / (1024**2))
                        
                        process_metrics.append(ProcessMetrics(
                            pid=proc.info['pid'],
                            name=proc.info['name'],
                            cpu_percent=proc.info['cpu_percent'] or 0.0,
                            memory_percent=proc.info['memory_percent'] or 0.0,
                            memory_rss_mb=memory_rss_mb,
                            threads=proc.info['num_threads'] or 0,
                            status=proc.info['status'],
                            create_time=proc.info['create_time'] or 0.0
                        ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to get process metrics: {e}")
        
        return process_metrics
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        current_metrics = self.get_current_metrics()
        process_metrics = self.get_process_metrics()
        
        return {
            'system_info': self.system_info,
            'hardware_status': asdict(self.hardware_status),
            'current_metrics': asdict(current_metrics) if current_metrics else None,
            'process_metrics': [asdict(p) for p in process_metrics],
            'thresholds': self.thresholds,
            'monitoring_active': self.is_running,
            'metrics_count': len(self.metrics_history),
            'last_updated': datetime.now().isoformat()
        }
    
    def get_performance_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """
        Get performance summary for the specified time period
        
        Args:
            minutes: Number of minutes to analyze
            
        Returns:
            Performance summary statistics
        """
        history = self.get_metrics_history(minutes)
        
        if not history:
            return {'error': 'No metrics available'}
        
        # Calculate statistics
        cpu_values = [m.cpu_percent for m in history]
        memory_values = [m.memory_percent for m in history]
        temperature_values = [m.temperature_celsius for m in history if m.temperature_celsius > 0]
        
        return {
            'time_period_minutes': minutes,
            'data_points': len(history),
            'cpu': {
                'current': cpu_values[-1] if cpu_values else 0,
                'average': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'minimum': min(cpu_values) if cpu_values else 0,
                'maximum': max(cpu_values) if cpu_values else 0
            },
            'memory': {
                'current': memory_values[-1] if memory_values else 0,
                'average': sum(memory_values) / len(memory_values) if memory_values else 0,
                'minimum': min(memory_values) if memory_values else 0,
                'maximum': max(memory_values) if memory_values else 0
            },
            'temperature': {
                'current': temperature_values[-1] if temperature_values else 0,
                'average': sum(temperature_values) / len(temperature_values) if temperature_values else 0,
                'minimum': min(temperature_values) if temperature_values else 0,
                'maximum': max(temperature_values) if temperature_values else 0
            },
            'alerts_triggered': self._count_threshold_violations(history)
        }
    
    def _count_threshold_violations(self, history: List[SystemMetrics]) -> Dict[str, int]:
        """Count threshold violations in the given history"""
        violations = {
            'cpu_warnings': 0,
            'cpu_critical': 0,
            'memory_warnings': 0,
            'memory_critical': 0,
            'disk_warnings': 0,
            'disk_critical': 0,
            'temperature_warnings': 0,
            'temperature_critical': 0
        }
        
        for metrics in history:
            if metrics.cpu_percent >= self.thresholds['cpu_critical']:
                violations['cpu_critical'] += 1
            elif metrics.cpu_percent >= self.thresholds['cpu_warning']:
                violations['cpu_warnings'] += 1
            
            if metrics.memory_percent >= self.thresholds['memory_critical']:
                violations['memory_critical'] += 1
            elif metrics.memory_percent >= self.thresholds['memory_warning']:
                violations['memory_warnings'] += 1
            
            if metrics.disk_percent >= self.thresholds['disk_critical']:
                violations['disk_critical'] += 1
            elif metrics.disk_percent >= self.thresholds['disk_warning']:
                violations['disk_warnings'] += 1
            
            if metrics.temperature_celsius >= self.thresholds['temperature_critical']:
                violations['temperature_critical'] += 1
            elif metrics.temperature_celsius >= self.thresholds['temperature_warning']:
                violations['temperature_warnings'] += 1
        
        return violations

def main():
    """Demo function for system monitor"""
    monitor = SystemMonitor()
    
    print("Pi5 Face Recognition - System Monitor")
    print("=" * 50)
    
    # Start monitoring
    monitor.start_monitoring()
    
    try:
        # Show live updates for 30 seconds
        for i in range(6):
            time.sleep(5)
            
            # Get current status
            status = monitor.get_system_status()
            current = status.get('current_metrics')
            
            if current:
                print(f"\nUpdate {i+1}/6:")
                print(f"  CPU: {current['cpu_percent']:.1f}%")
                print(f"  Memory: {current['memory_percent']:.1f}%")
                print(f"  Temperature: {current['temperature_celsius']:.1f}°C")
                print(f"  Disk: {current['disk_percent']:.1f}%")
        
        # Show performance summary
        print("\nPerformance Summary (last 5 minutes):")
        summary = monitor.get_performance_summary(5)
        for category, stats in summary.items():
            if isinstance(stats, dict) and 'current' in stats:
                print(f"  {category.upper()}:")
                print(f"    Current: {stats['current']:.1f}")
                print(f"    Average: {stats['average']:.1f}")
                print(f"    Min/Max: {stats['minimum']:.1f}/{stats['maximum']:.1f}")
    
    except KeyboardInterrupt:
        print("\nStopping monitor...")
    
    finally:
        monitor.stop_monitoring()
        print("System monitor stopped")

if __name__ == "__main__":
    main()