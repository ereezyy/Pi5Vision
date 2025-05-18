#!/bin/bash
# Installation script for Raspberry Pi 5 Face Recognition System with Hailo AI HAT+
# This script installs all necessary dependencies and sets up the system

set -e  # Exit on error

# Display welcome message
echo "====================================================="
echo "Raspberry Pi 5 Face Recognition System with Hailo HAT+"
echo "Installation Script"
echo "====================================================="
echo

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "ERROR: This script must be run on a Raspberry Pi."
    echo "Current device: $(cat /proc/device-tree/model 2>/dev/null || echo 'Unknown')"
    exit 1
fi

# Check for Raspberry Pi 5
if ! grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
    echo "WARNING: This system is designed for Raspberry Pi 5."
    echo "Current device: $(cat /proc/device-tree/model 2>/dev/null || echo 'Unknown')"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)."
    exit 1
fi

# Create installation directory
INSTALL_DIR="/opt/pi5-face-recognition"
echo "Creating installation directory at $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Function to check if Hailo HAT is detected
check_hailo_hat() {
    if lspci | grep -q "Hailo"; then
        echo "Hailo HAT detected."
        return 0
    else
        echo "WARNING: Hailo HAT not detected."
        echo "Make sure the Hailo AI HAT+ is properly installed."
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        return 1
    fi
}

# Function to install system dependencies
install_system_dependencies() {
    echo "Updating package lists..."
    apt-get update -y

    echo "Installing system dependencies..."
    apt-get install -y \
        python3-pip \
        python3-opencv \
        python3-numpy \
        python3-gi \
        python3-gi-cairo \
        gir1.2-gtk-3.0 \
        libsqlite3-dev \
        gstreamer1.0-tools \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        gstreamer1.0-libav \
        dkms \
        v4l-utils
}

# Function to install Hailo drivers and software
install_hailo_software() {
    echo "Installing Hailo drivers and software..."
    
    # Check if Hailo drivers are already installed
    if command -v hailortcli >/dev/null 2>&1; then
        HAILO_VERSION=$(hailortcli fw-control identify 2>/dev/null | grep "Firmware Version" | awk '{print $3}')
        echo "Hailo software already installed (version $HAILO_VERSION)."
        
        # Check if version is at least 4.18.0
        if [[ "$HAILO_VERSION" < "4.18.0" ]]; then
            echo "Upgrading Hailo software to version 4.18.0..."
            # Download and install PCIe driver
            wget -O hailort-pcie-driver_4.18.0_all.deb https://hailo.ai/developer-zone/downloads/hailort-pcie-driver_4.18.0_all.deb
            dpkg --install hailort-pcie-driver_4.18.0_all.deb
            
            # Download and install HailoRT
            wget -O hailort_4.18.0_arm64.deb https://hailo.ai/developer-zone/downloads/hailort_4.18.0_arm64.deb
            dpkg --install hailort_4.18.0_arm64.deb
            
            # Download and install Python bindings
            pip3 install https://hailo.ai/developer-zone/downloads/hailort-4.18.0-cp311-cp311-linux_aarch64.whl
        fi
    else
        echo "Installing Hailo software version 4.18.0..."
        # Download and install PCIe driver
        wget -O hailort-pcie-driver_4.18.0_all.deb https://hailo.ai/developer-zone/downloads/hailort-pcie-driver_4.18.0_all.deb
        dpkg --install hailort-pcie-driver_4.18.0_all.deb
        
        # Download and install HailoRT
        wget -O hailort_4.18.0_arm64.deb https://hailo.ai/developer-zone/downloads/hailort_4.18.0_arm64.deb
        dpkg --install hailort_4.18.0_arm64.deb
        
        # Download and install Python bindings
        pip3 install https://hailo.ai/developer-zone/downloads/hailort-4.18.0-cp311-cp311-linux_aarch64.whl
    fi
    
    # Install TAPPAS
    echo "Installing TAPPAS..."
    mkdir -p /opt/tappas
    cd /opt/tappas
    git clone https://github.com/hailo-ai/tappas
    cd tappas/tappas_v3.29.1
    
    # Check if EXTERNALLY-MANAGED exists and back it up if needed
    if [ -f "/usr/lib/python3.11/EXTERNALLY-MANAGED" ]; then
        mv /usr/lib/python3.11/EXTERNALLY-MANAGED /usr/lib/python3.11/EXTERNALLY-MANAGED.bak
    fi
    
    # Modify setup.py to fix installation on Raspberry Pi
    sed -i 's/lsb_release = list(filter(lambda x: '\''RELEASE'\'' in x,\n                          Path('\''/etc\/lsb-release'\'').read_text().split('\''\\n'\'')))\[0\].split('\''='\'')\\[1\\].replace('\''.'\', '\''_'\'')/required = Path(f'\''requirements_20_04.txt'\'').read_text().splitlines()/' tools/run_app/setup.py
    
    # Install TAPPAS
    ./install.sh --skip-hailort
    
    # Restore EXTERNALLY-MANAGED if it was backed up
    if [ -f "/usr/lib/python3.11/EXTERNALLY-MANAGED.bak" ]; then
        mv /usr/lib/python3.11/EXTERNALLY-MANAGED.bak /usr/lib/python3.11/EXTERNALLY-MANAGED
    fi
}

# Function to download face recognition models
download_models() {
    echo "Downloading face recognition models..."
    mkdir -p "$INSTALL_DIR/models"
    
    # Download RetinaFace model
    wget -O "$INSTALL_DIR/models/retinaface_mobilenet_v1.hef" https://hailo.ai/developer-zone/downloads/models/retinaface_mobilenet_v1.hef
    
    echo "Models downloaded to $INSTALL_DIR/models"
}

# Function to install Python dependencies
install_python_dependencies() {
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
}

# Function to copy application files
copy_application_files() {
    echo "Copying application files..."
    cp -r src/* "$INSTALL_DIR/"
    cp config.json "$INSTALL_DIR/"
    cp requirements.txt "$INSTALL_DIR/"
    cp README.md "$INSTALL_DIR/"
    cp LICENSE "$INSTALL_DIR/"
    
    # Create data directories
    mkdir -p "$INSTALL_DIR/database"
    mkdir -p "$INSTALL_DIR/alerts"
    mkdir -p "$INSTALL_DIR/faces"
    mkdir -p "$INSTALL_DIR/logs"
    
    # Set permissions
    chown -R pi:pi "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
}

# Function to create systemd service
create_systemd_service() {
    echo "Creating systemd service..."
    cat > /etc/systemd/system/face-recognition.service << EOF
[Unit]
Description=Raspberry Pi 5 Face Recognition System
After=network.target

[Service]
ExecStart=/usr/bin/python3 $INSTALL_DIR/face_tracking.py --config $INSTALL_DIR/config.json --model $INSTALL_DIR/models/retinaface_mobilenet_v1.hef --gstreamer
WorkingDirectory=$INSTALL_DIR
StandardOutput=journal
StandardError=journal
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload
    
    # Enable service to start on boot
    systemctl enable face-recognition.service
    
    echo "Systemd service created and enabled."
}

# Function to create desktop shortcut
create_desktop_shortcut() {
    echo "Creating desktop shortcut..."
    mkdir -p /home/pi/Desktop
    
    cat > /home/pi/Desktop/Face-Recognition.desktop << EOF
[Desktop Entry]
Name=Face Recognition
Comment=Raspberry Pi 5 Face Recognition System
Exec=/usr/bin/python3 $INSTALL_DIR/face_tracking.py --config $INSTALL_DIR/config.json --model $INSTALL_DIR/models/retinaface_mobilenet_v1.hef --gstreamer
Icon=/usr/share/icons/Adwaita/48x48/devices/camera-web.png
Terminal=true
Type=Application
Categories=Utility;
EOF

    # Set permissions
    chmod +x /home/pi/Desktop/Face-Recognition.desktop
    chown pi:pi /home/pi/Desktop/Face-Recognition.desktop
    
    echo "Desktop shortcut created."
}

# Main installation process
echo "Starting installation process..."

# Check for Hailo HAT
check_hailo_hat

# Install system dependencies
install_system_dependencies

# Install Hailo software
install_hailo_software

# Download models
download_models

# Install Python dependencies
install_python_dependencies

# Copy application files
copy_application_files

# Create systemd service
create_systemd_service

# Create desktop shortcut
create_desktop_shortcut

echo
echo "====================================================="
echo "Installation completed successfully!"
echo
echo "To start the face recognition system:"
echo "  1. Reboot the Raspberry Pi: sudo reboot"
echo "  2. The system will start automatically on boot"
echo "  3. To start manually: sudo systemctl start face-recognition"
echo
echo "To view logs: sudo journalctl -u face-recognition -f"
echo "====================================================="
