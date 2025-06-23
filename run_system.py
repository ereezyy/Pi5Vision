#!/usr/bin/env python3
"""
Main runner for Pi5 Face Recognition System
Orchestrates all components and provides unified startup
"""

import os
import sys
import asyncio
import signal
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

class Pi5FaceRecognitionSystem:
    """Main system orchestrator"""
    
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

async def main():
    """Main function"""
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

if __name__ == "__main__":
    asyncio.run(main())