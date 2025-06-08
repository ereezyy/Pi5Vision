#!/bin/bash
# Installation script for Raspberry Pi 5 Face Recognition System with Hailo AI HAT+
# WebContainer-compatible version - removes sudo dependencies and system-level operations

set -e  # Exit on error

# Display welcome message
echo "====================================================="
echo "Raspberry Pi 5 Face Recognition System with Hailo HAT+"
echo "WebContainer Installation Script"
echo "====================================================="
echo

# Note about WebContainer limitations
echo "NOTE: This is a WebContainer environment simulation."
echo "Some features will be simulated for demonstration purposes."
echo

# Create installation directory (using relative paths for WebContainer)
INSTALL_DIR="./pi5-face-recognition"
echo "Creating installation directory at $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Function to check if we're in WebContainer
check_webcontainer() {
    if [ -n "$WEBCONTAINER" ] || [ ! -f "/proc/version" ]; then
        echo "WebContainer environment detected."
        echo "Skipping hardware-specific checks and installations."
        return 0
    else
        echo "Physical Raspberry Pi environment detected."
        return 1
    fi
}

# Function to simulate system dependencies installation
install_system_dependencies() {
    echo "Simulating system dependencies installation..."
    echo "In a real Raspberry Pi environment, this would install:"
    echo "  - python3-pip"
    echo "  - python3-opencv"
    echo "  - python3-numpy"
    echo "  - GStreamer components"
    echo "  - V4L utilities"
    echo "Dependencies simulation complete."
}

# Function to simulate Hailo software installation
install_hailo_software() {
    echo "Simulating Hailo drivers and software installation..."
    echo "In a real Raspberry Pi environment, this would:"
    echo "  - Download and install Hailo PCIe driver"
    echo "  - Install HailoRT runtime"
    echo "  - Install Python bindings"
    echo "  - Install TAPPAS framework"
    echo "Hailo software simulation complete."
}

# Function to create mock models directory
download_models() {
    echo "Creating models directory..."
    mkdir -p "$INSTALL_DIR/models"
    
    # Create a mock model file for demonstration
    echo "# Mock Hailo model file for WebContainer demonstration" > "$INSTALL_DIR/models/retinaface_mobilenet_v1.hef"
    echo "# In a real environment, this would be the actual Hailo model binary"
    
    echo "Mock models created in $INSTALL_DIR/models"
}

# Function to install Python dependencies (WebContainer compatible)
install_python_dependencies() {
    echo "Installing Python dependencies..."
    
    # Check if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        # Install only WebContainer-compatible packages
        echo "Installing WebContainer-compatible Python packages..."
        
        # Create a WebContainer-compatible requirements file
        cat > webcontainer-requirements.txt << EOF
# WebContainer-compatible requirements
numpy>=1.20.0
pillow>=8.0.0
fastapi>=0.68.0
uvicorn>=0.15.0
jinja2>=3.0.0
python-multipart>=0.0.5
pydantic>=1.8.0
EOF
        
        # Install using pip
        python3 -m pip install -r webcontainer-requirements.txt || echo "Some packages may not be available in WebContainer"
    else
        echo "requirements.txt not found, skipping Python dependencies"
    fi
}

# Function to copy application files
copy_application_files() {
    echo "Copying application files..."
    
    # Copy source files if they exist
    if [ -d "src" ]; then
        cp -r src/* "$INSTALL_DIR/" 2>/dev/null || echo "Some source files may not exist"
    fi
    
    # Copy config files if they exist
    [ -f "config.json" ] && cp config.json "$INSTALL_DIR/" || echo "config.json not found"
    [ -f "requirements.txt" ] && cp requirements.txt "$INSTALL_DIR/" || echo "requirements.txt not found"
    [ -f "README.md" ] && cp README.md "$INSTALL_DIR/" || echo "README.md not found"
    [ -f "LICENSE" ] && cp LICENSE "$INSTALL_DIR/" || echo "LICENSE not found"
    
    # Create data directories
    mkdir -p "$INSTALL_DIR/database"
    mkdir -p "$INSTALL_DIR/alerts"
    mkdir -p "$INSTALL_DIR/faces"
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/static"
    mkdir -p "$INSTALL_DIR/templates"
    
    # Create basic template files for WebContainer
    create_webcontainer_templates
    
    echo "Application files copied to $INSTALL_DIR"
}

# Function to create basic templates for WebContainer
create_webcontainer_templates() {
    echo "Creating WebContainer-compatible templates..."
    
    # Create basic HTML template
    cat > "$INSTALL_DIR/templates/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pi5 Face Recognition Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .status-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }
        .demo-notice {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Pi5 Face Recognition Dashboard</h1>
            <p>Raspberry Pi 5 with Hailo AI HAT+ - WebContainer Demo</p>
        </div>
        
        <div class="demo-notice">
            <strong>Demo Mode:</strong> This is a WebContainer simulation of the Raspberry Pi 5 Face Recognition System. 
            In a real deployment, this would connect to actual hardware and provide live face recognition capabilities.
        </div>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>System Status</h3>
                <p>Status: <span style="color: green;">Simulated</span></p>
                <p>Environment: WebContainer</p>
            </div>
            
            <div class="status-card">
                <h3>Camera</h3>
                <p>Status: <span style="color: orange;">Simulated</span></p>
                <p>Resolution: 1280x720</p>
            </div>
            
            <div class="status-card">
                <h3>Hailo AI HAT+</h3>
                <p>Status: <span style="color: orange;">Simulated</span></p>
                <p>Model: RetinaFace</p>
            </div>
            
            <div class="status-card">
                <h3>Recognition</h3>
                <p>Active: <span style="color: green;">Demo Mode</span></p>
                <p>Faces Detected: 0</p>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <p><em>This demo showcases the web interface that would be available on a real Raspberry Pi 5 system.</em></p>
        </div>
    </div>
</body>
</html>
EOF
}

# Function to create a WebContainer-compatible startup script
create_startup_script() {
    echo "Creating WebContainer startup script..."
    
    cat > "$INSTALL_DIR/start_demo.py" << 'EOF'
#!/usr/bin/env python3
"""
WebContainer Demo Startup Script for Pi5 Face Recognition System
"""

import os
import sys
import time
import json
from pathlib import Path

def main():
    print("=" * 60)
    print("Pi5 Face Recognition System - WebContainer Demo")
    print("=" * 60)
    print()
    
    print("🚀 Starting demo server...")
    print("📁 Working directory:", os.getcwd())
    print("🐍 Python version:", sys.version)
    print()
    
    # Check if we can import required modules
    try:
        import numpy
        print("✅ NumPy available")
    except ImportError:
        print("❌ NumPy not available")
    
    try:
        import PIL
        print("✅ Pillow available")
    except ImportError:
        print("❌ Pillow not available")
    
    try:
        import fastapi
        print("✅ FastAPI available")
    except ImportError:
        print("❌ FastAPI not available")
    
    print()
    print("🌐 In a real deployment, the web dashboard would be available at:")
    print("   http://raspberry-pi-ip:8080")
    print()
    print("📋 Features available in real deployment:")
    print("   • Live camera feed with face detection")
    print("   • Real-time face recognition using Hailo AI")
    print("   • Person enrollment and management")
    print("   • Alert system for unknown faces")
    print("   • Analytics and reporting")
    print("   • Privacy controls and data management")
    print()
    print("🔧 This WebContainer demo simulates the system for development purposes.")
    print("   Deploy to actual Raspberry Pi 5 hardware for full functionality.")

if __name__ == "__main__":
    main()
EOF
    
    chmod +x "$INSTALL_DIR/start_demo.py"
}

# Main installation process
echo "Starting WebContainer-compatible installation process..."

# Check environment
check_webcontainer
IS_WEBCONTAINER=$?

# Install system dependencies (simulated)
install_system_dependencies

# Install Hailo software (simulated)
install_hailo_software

# Download models (create mock files)
download_models

# Install Python dependencies (WebContainer compatible)
install_python_dependencies

# Copy application files
copy_application_files

# Create startup script
create_startup_script

echo
echo "====================================================="
echo "WebContainer installation completed successfully!"
echo
echo "To start the demo:"
echo "  cd $INSTALL_DIR"
echo "  python3 start_demo.py"
echo
echo "Note: This is a WebContainer simulation."
echo "For full functionality, deploy to Raspberry Pi 5 hardware."
echo "====================================================="