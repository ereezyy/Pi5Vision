#!/usr/bin/env python3
"""
WebContainer Demo for Pi5 Face Recognition System
This script provides a working demonstration of the system in WebContainer environment
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

def check_environment():
    """Check the current environment and available modules"""
    print("🔍 Environment Check")
    print("-" * 40)
    
    # Check Python version
    print(f"Python Version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Working Directory: {os.getcwd()}")
    print()
    
    # Check available modules
    modules_to_check = [
        'numpy', 'PIL', 'fastapi', 'uvicorn', 'jinja2', 
        'pydantic', 'pathlib', 'json', 'datetime'
    ]
    
    available_modules = []
    missing_modules = []
    
    for module in modules_to_check:
        try:
            __import__(module)
            available_modules.append(module)
            print(f"✅ {module}")
        except ImportError:
            missing_modules.append(module)
            print(f"❌ {module}")
    
    print()
    return available_modules, missing_modules

def create_demo_structure():
    """Create the demo directory structure"""
    print("📁 Creating Demo Structure")
    print("-" * 40)
    
    directories = [
        'demo/static',
        'demo/templates', 
        'demo/models',
        'demo/database',
        'demo/alerts',
        'demo/faces',
        'demo/logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created: {directory}")
    
    print()

def create_demo_files():
    """Create demo configuration and template files"""
    print("📄 Creating Demo Files")
    print("-" * 40)
    
    # Create demo config
    config = {
        "system": {
            "name": "Pi5 Face Recognition Demo",
            "version": "2.0.0",
            "environment": "webcontainer"
        },
        "camera": {
            "device_id": 0,
            "resolution": [1280, 720],
            "fps": 30
        },
        "hailo": {
            "model_path": "models/retinaface_mobilenet_v1.hef",
            "confidence_threshold": 0.5
        },
        "web": {
            "host": "0.0.0.0",
            "port": 8080,
            "debug": True
        }
    }
    
    with open('demo/config.json', 'w') as f:
        json.dump(config, f, indent=2)
    print("Created: demo/config.json")
    
    # Create simple HTML template
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pi5 Face Recognition - WebContainer Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .status { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .warning { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #ffc107; }
        .feature { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Pi5 Face Recognition System</h1>
            <h2>WebContainer Demo</h2>
        </div>
        
        <div class="warning">
            <strong>Demo Environment:</strong> This is a WebContainer simulation. 
            Full functionality requires deployment on Raspberry Pi 5 hardware with Hailo AI HAT+.
        </div>
        
        <div class="status">
            <h3>✅ Demo Status: Active</h3>
            <p>Environment: WebContainer Browser Runtime</p>
            <p>Timestamp: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </div>
        
        <div class="feature">
            <h3>🎯 System Features</h3>
            <ul>
                <li>Real-time face detection using Hailo AI acceleration</li>
                <li>Face recognition and person identification</li>
                <li>Web-based dashboard and management interface</li>
                <li>Alert system for unknown faces</li>
                <li>Privacy controls and data management</li>
                <li>Analytics and reporting capabilities</li>
            </ul>
        </div>
        
        <div class="feature">
            <h3>🔧 Hardware Requirements</h3>
            <ul>
                <li>Raspberry Pi 5 (8GB recommended)</li>
                <li>Hailo AI HAT+ acceleration module</li>
                <li>USB camera or Pi Camera Module 3</li>
                <li>MicroSD card (64GB+ recommended)</li>
                <li>Power supply and cooling</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <p><em>Ready for deployment to Raspberry Pi 5 hardware!</em></p>
        </div>
    </div>
</body>
</html>"""
    
    with open('demo/templates/index.html', 'w') as f:
        f.write(html_template)
    print("Created: demo/templates/index.html")
    
    # Create mock model file
    with open('demo/models/retinaface_mobilenet_v1.hef', 'w') as f:
        f.write("# Mock Hailo model file for WebContainer demo\n")
        f.write("# In real deployment, this would be the binary model file\n")
    print("Created: demo/models/retinaface_mobilenet_v1.hef")
    
    print()

def run_simple_server():
    """Run a simple HTTP server to serve the demo"""
    print("🌐 Starting Demo Server")
    print("-" * 40)
    
    try:
        import http.server
        import socketserver
        import webbrowser
        from threading import Timer
        
        PORT = 8080
        
        class DemoHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory='demo', **kwargs)
            
            def do_GET(self):
                if self.path == '/':
                    self.path = '/templates/index.html'
                return super().do_GET()
        
        with socketserver.TCPServer(("", PORT), DemoHandler) as httpd:
            print(f"✅ Demo server running at http://localhost:{PORT}")
            print("📱 Open the URL above to view the demo interface")
            print("🛑 Press Ctrl+C to stop the server")
            print()
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n🛑 Demo server stopped")
                
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("📄 You can manually open demo/templates/index.html in a browser")

def main():
    """Main demo function"""
    print("=" * 60)
    print("🚀 Pi5 Face Recognition System - WebContainer Demo")
    print("=" * 60)
    print()
    
    # Check environment
    available, missing = check_environment()
    
    # Create demo structure
    create_demo_structure()
    
    # Create demo files
    create_demo_files()
    
    # Show summary
    print("📊 Demo Summary")
    print("-" * 40)
    print(f"✅ Available modules: {len(available)}")
    print(f"❌ Missing modules: {len(missing)}")
    print(f"📁 Demo files created in: {os.path.abspath('demo')}")
    print()
    
    # Ask user if they want to start the server
    try:
        response = input("🌐 Start demo web server? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            run_simple_server()
        else:
            print("📄 Demo files created. Open demo/templates/index.html to view the interface.")
    except (EOFError, KeyboardInterrupt):
        print("\n📄 Demo files created. Open demo/templates/index.html to view the interface.")

if __name__ == "__main__":
    main()