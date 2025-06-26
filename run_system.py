#!/usr/bin/env python3
"""
Main runner for Pi5 Face Recognition System
Orchestrates all components and provides unified startup
WebContainer-compatible with fallback to demo mode
"""

import os
import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.append('src')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def detect_environment():
    """Detect if running in WebContainer or full system"""
    # Check for WebContainer indicators
    webcontainer_indicators = [
        os.environ.get('WEBCONTAINER') == 'true',
        'webcontainer' in os.environ.get('NODE_ENV', '').lower(),
        not os.path.exists('/proc/cpuinfo'),  # No real /proc in WebContainer
        os.environ.get('SHELL', '').endswith('zsh'),  # WebContainer uses zsh
    ]
    
    return any(webcontainer_indicators)

def check_required_modules():
    """Check if required modules are available"""
    try:
        import select
        import asyncio
        return True
    except ImportError as e:
        logger.warning(f"Required module not available: {e}")
        return False

class WebContainerSystem:
    """WebContainer-compatible system runner"""
    
    def __init__(self):
        self.running = False
        logger.info("Running in WebContainer compatibility mode")
    
    def start(self):
        """Start WebContainer-compatible demo"""
        logger.info("Starting Pi5 Face Recognition System (WebContainer Demo)...")
        
        try:
            # Import and run the demo
            from demo_runner import WebContainerFaceRecognitionDemo
            
            demo = WebContainerFaceRecognitionDemo()
            demo.show_system_capabilities()
            
            print("\n" + "="*60)
            print("🔄 WebContainer Demo Mode Active")
            print("📱 Full system features simulated for demonstration")
            print("🚀 Deploy to Raspberry Pi 5 for complete functionality")
            print("="*60)
            
            input("\n📋 Press Enter to start system initialization...")
            
            if demo.initialize_system():
                input("\n🚀 Press Enter to start real-time processing...")
                demo.start_real_time_processing()
                
        except ImportError as e:
            logger.error(f"Demo runner not available: {e}")
            self.show_installation_guide()
        except Exception as e:
            logger.error(f"Error starting WebContainer demo: {e}")
    
    def show_installation_guide(self):
        """Show installation guide for full system"""
        print("\n" + "="*60)
        print("🔧 FULL SYSTEM INSTALLATION REQUIRED")
        print("="*60)
        print("This is a WebContainer environment with limited capabilities.")
        print("For the complete Pi5 Face Recognition System:")
        print()
        print("1. 📦 Deploy to Raspberry Pi 5 with Hailo AI HAT+")
        print("2. 🔧 Run the installation script:")
        print("   sudo chmod +x install_pi5.sh")
        print("   sudo ./install_pi5.sh")
        print("3. 🚀 Start the full system:")
        print("   python3 run_system.py")
        print()
        print("WebContainer limitations:")
        print("- No asyncio/select module support")
        print("- No hardware access (cameras, AI HAT+)")
        print("- Simulated functionality only")
        print("="*60)

class Pi5FaceRecognitionSystem:
    """Full system orchestrator for Raspberry Pi"""
    
    def __init__(self):
        self.running = False
        self.components = {}
        
    async def start(self):
        """Start the complete system"""
        logger.info("Starting Pi5 Face Recognition System...")
        
        try:
            # Start web dashboard
            from enhanced_web_dashboard import EnhancedWebDashboard
            self.components['dashboard'] = EnhancedWebDashboard()
            
            # Start system monitoring if available
            try:
                from system_monitor import SystemMonitor
                self.components['monitor'] = SystemMonitor()
                self.components['monitor'].start_monitoring()
                logger.info("System monitoring started")
            except ImportError:
                logger.warning("System monitoring not available")
            
            # Start face recognition core if available
            try:
                from core_engine import CoreEngine
                self.components['core'] = CoreEngine()
                await self.components['core'].initialize()
                self.components['core'].start()
                logger.info("Face recognition core started")
            except ImportError:
                logger.warning("Face recognition core not available")
            
            self.running = True
            logger.info("System startup complete")
            
            # Run web dashboard
            self.components['dashboard'].run()
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            await self.stop()
    
    async def stop(self):
        """Stop the complete system"""
        logger.info("Stopping Pi5 Face Recognition System...")
        
        self.running = False
        
        # Stop all components
        for name, component in self.components.items():
            try:
                if hasattr(component, 'stop'):
                    component.stop()
                elif hasattr(component, 'stop_monitoring'):
                    component.stop_monitoring()
                logger.info(f"Stopped {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        
        logger.info("System shutdown complete")

def main():
    """Main function with environment detection"""
    print("🔍 Pi5 Face Recognition System")
    print("=" * 40)
    
    # Detect environment
    is_webcontainer = detect_environment()
    has_required_modules = check_required_modules()
    
    if is_webcontainer or not has_required_modules:
        logger.info("WebContainer environment detected")
        system = WebContainerSystem()
        system.start()
    else:
        logger.info("Full system environment detected")
        try:
            import asyncio
            import signal
            
            async def run_full_system():
                system = Pi5FaceRecognitionSystem()
                
                # Set up signal handlers
                def signal_handler(sig, frame):
                    logger.info("Received shutdown signal")
                    asyncio.create_task(system.stop())
                
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
                
                try:
                    await system.start()
                except KeyboardInterrupt:
                    logger.info("Interrupted by user")
                finally:
                    await system.stop()
            
            asyncio.run(run_full_system())
            
        except Exception as e:
            logger.error(f"Failed to start full system: {e}")
            logger.info("Falling back to WebContainer demo mode...")
            system = WebContainerSystem()
            system.start()

if __name__ == "__main__":
    main()