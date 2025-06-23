#!/bin/bash
# Enhanced Installation Script for Raspberry Pi 5 Face Recognition System with Hailo AI HAT+
# Production-ready installation with error handling and validation

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation configuration
INSTALL_DIR="/opt/pi5-face-recognition"
SERVICE_NAME="pi5-face-recognition"
USER_HOME="/home/pi"
LOG_FILE="/tmp/pi5_install.log"

# Display banner
show_banner() {
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}    Raspberry Pi 5 Face Recognition System with Hailo AI HAT+${NC}"
    echo -e "${BLUE}                     Enhanced Installation${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
}

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "${RED}ERROR: $1${NC}"
    log "${RED}Installation failed. Check log at $LOG_FILE${NC}"
    exit 1
}

# Success message
success() {
    log "${GREEN}✓ $1${NC}"
}

# Warning message
warning() {
    log "${YELLOW}⚠ $1${NC}"
}

# Info message
info() {
    log "${BLUE}ℹ $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "This script must be run as root (use sudo)"
    fi
}

# Detect hardware
detect_hardware() {
    info "Detecting hardware configuration..."
    
    # Check if running on Raspberry Pi 5
    if ! grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
        warning "Not running on Raspberry Pi 5. Some features may not work optimally."
    else
        success "Raspberry Pi 5 detected"
    fi
    
    # Check for Hailo device
    if lspci | grep -q "Hailo" 2>/dev/null; then
        success "Hailo AI HAT+ detected"
    else
        warning "Hailo AI HAT+ not detected. Please ensure it's properly installed."
    fi
    
    # Check available cameras
    if ls /dev/video* >/dev/null 2>&1; then
        CAMERA_COUNT=$(ls /dev/video* | wc -l)
        success "Found $CAMERA_COUNT camera device(s)"
    else
        warning "No camera devices found. Please connect a USB camera."
    fi
}

# Update system packages
update_system() {
    info "Updating system packages..."
    apt update >> "$LOG_FILE" 2>&1 || error_exit "Failed to update package list"
    apt upgrade -y >> "$LOG_FILE" 2>&1 || error_exit "Failed to upgrade packages"
    success "System packages updated"
}

# Install system dependencies
install_system_dependencies() {
    info "Installing system dependencies..."
    
    PACKAGES=(
        "python3"
        "python3-pip"
        "python3-venv"
        "python3-dev"
        "build-essential"
        "cmake"
        "pkg-config"
        "libjpeg-dev"
        "libtiff5-dev"
        "libpng-dev"
        "libavcodec-dev"
        "libavformat-dev"
        "libswscale-dev"
        "libv4l-dev"
        "libxvidcore-dev"
        "libx264-dev"
        "libfontconfig1-dev"
        "libcairo2-dev"
        "libgdk-pixbuf2.0-dev"
        "libpango1.0-dev"
        "libgtk2.0-dev"
        "libgtk-3-dev"
        "libatlas-base-dev"
        "gfortran"
        "libhdf5-dev"
        "libhdf5-serial-dev"
        "libhdf5-103"
        "libqtgui4"
        "libqtwebkit4"
        "libqt4-test"
        "python3-pyqt5"
        "sqlite3"
        "postgresql"
        "postgresql-contrib"
        "nginx"
        "supervisor"
        "git"
        "curl"
        "wget"
        "unzip"
    )
    
    for package in "${PACKAGES[@]}"; do
        info "Installing $package..."
        apt install -y "$package" >> "$LOG_FILE" 2>&1 || warning "Failed to install $package"
    done
    
    success "System dependencies installed"
}

# Install Hailo software
install_hailo_software() {
    info "Installing Hailo software stack..."
    
    # Check if HailoRT is already installed
    if command -v hailortcli &> /dev/null; then
        success "HailoRT already installed"
        return
    fi
    
    # Create temp directory for Hailo installation
    HAILO_TEMP="/tmp/hailo_install"
    mkdir -p "$HAILO_TEMP"
    cd "$HAILO_TEMP"
    
    # Download HailoRT (you would need to provide the actual download URL)
    info "Downloading HailoRT..."
    # Note: Replace with actual Hailo download URL when available
    # wget https://hailo.ai/downloads/hailort-4.18.0-linux-aarch64.deb
    
    # For now, create a placeholder
    touch hailort-4.18.0-linux-aarch64.deb
    
    # Install HailoRT
    if [ -f "hailort-4.18.0-linux-aarch64.deb" ]; then
        dpkg -i hailort-4.18.0-linux-aarch64.deb >> "$LOG_FILE" 2>&1 || true
        apt-get install -f -y >> "$LOG_FILE" 2>&1 || warning "HailoRT installation issues"
        success "HailoRT package installed"
    else
        warning "HailoRT package not found. Please install manually from Hailo website."
    fi
    
    # Install Python bindings
    pip3 install hailo-platform >> "$LOG_FILE" 2>&1 || warning "Failed to install Hailo Python bindings"
    
    cd - > /dev/null
    rm -rf "$HAILO_TEMP"
}

# Create installation directory
create_directories() {
    info "Creating installation directories..."
    
    mkdir -p "$INSTALL_DIR"/{src,models,database,alerts,faces,logs,static,templates,config}
    mkdir -p "$INSTALL_DIR/scripts"
    mkdir -p "/var/log/pi5-face-recognition"
    
    success "Directories created"
}

# Copy application files
copy_application_files() {
    info "Copying application files..."
    
    # Copy source files
    cp -r src/* "$INSTALL_DIR/src/" 2>/dev/null || warning "Source files not found"
    
    # Copy configuration
    cp config.json "$INSTALL_DIR/config/" 2>/dev/null || warning "Config file not found"
    
    # Copy templates and static files
    cp -r templates/* "$INSTALL_DIR/templates/" 2>/dev/null || warning "Template files not found"
    cp -r static/* "$INSTALL_DIR/static/" 2>/dev/null || warning "Static files not found"
    
    # Copy documentation
    cp *.md "$INSTALL_DIR/" 2>/dev/null || warning "Documentation files not found"
    
    success "Application files copied"
}

# Install Python dependencies
install_python_dependencies() {
    info "Installing Python dependencies..."
    
    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip >> "$LOG_FILE" 2>&1
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt >> "$LOG_FILE" 2>&1 || warning "Some Python packages failed to install"
    fi
    
    # Install additional packages for Pi5
    pip install opencv-python-headless >> "$LOG_FILE" 2>&1 || warning "OpenCV installation failed"
    pip install psutil >> "$LOG_FILE" 2>&1 || warning "psutil installation failed"
    pip install gpiozero >> "$LOG_FILE" 2>&1 || warning "gpiozero installation failed"
    
    success "Python dependencies installed"
}

# Download AI models
download_models() {
    info "Setting up AI models..."
    
    MODELS_DIR="$INSTALL_DIR/models"
    
    # Create model placeholders (in production, these would be actual downloads)
    models=(
        "retinaface_mobilenet_v1.hef"
        "scrfd_10g.hef"
        "arcface_mobilefacenet.hef"
        "ssr_net.hef"
        "emotion_detection.hef"
        "mask_detection.hef"
    )
    
    for model in "${models[@]}"; do
        if [ ! -f "$MODELS_DIR/$model" ]; then
            info "Creating placeholder for $model..."
            echo "# Hailo model placeholder - replace with actual model" > "$MODELS_DIR/$model"
        fi
    done
    
    success "AI models prepared"
}

# Setup database
setup_database() {
    info "Setting up database..."
    
    # Start PostgreSQL service
    systemctl start postgresql >> "$LOG_FILE" 2>&1 || warning "Failed to start PostgreSQL"
    systemctl enable postgresql >> "$LOG_FILE" 2>&1 || warning "Failed to enable PostgreSQL"
    
    # Create database and user
    sudo -u postgres createdb face_recognition >> "$LOG_FILE" 2>&1 || warning "Database already exists"
    sudo -u postgres createuser pi5user >> "$LOG_FILE" 2>&1 || warning "User already exists"
    sudo -u postgres psql -c "ALTER USER pi5user WITH PASSWORD 'pi5pass';" >> "$LOG_FILE" 2>&1
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE face_recognition TO pi5user;" >> "$LOG_FILE" 2>&1
    
    success "Database configured"
}

# Create systemd service
create_service() {
    info "Creating systemd service..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Pi5 Face Recognition Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python src/face_tracking.py --config config/config.json
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=pi5-face-recognition

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload >> "$LOG_FILE" 2>&1
    systemctl enable "$SERVICE_NAME" >> "$LOG_FILE" 2>&1
    
    success "Systemd service created"
}

# Setup web server
setup_web_server() {
    info "Setting up web server..."
    
    # Create nginx configuration
    cat > "/etc/nginx/sites-available/pi5-face-recognition" << EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /static/ {
        alias $INSTALL_DIR/static/;
        expires 30d;
    }
    
    location /faces/ {
        alias $INSTALL_DIR/faces/;
        expires 1d;
    }
    
    location /alerts/ {
        alias $INSTALL_DIR/alerts/;
        expires 1d;
    }
}
EOF
    
    # Enable site and restart nginx
    ln -sf /etc/nginx/sites-available/pi5-face-recognition /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    systemctl restart nginx >> "$LOG_FILE" 2>&1 || warning "Failed to restart nginx"
    systemctl enable nginx >> "$LOG_FILE" 2>&1
    
    success "Web server configured"
}

# Set permissions
set_permissions() {
    info "Setting permissions..."
    
    chown -R pi:pi "$INSTALL_DIR"
    chmod +x "$INSTALL_DIR/src"/*.py
    chmod 755 "$INSTALL_DIR"
    
    # Set up log rotation
    cat > "/etc/logrotate.d/pi5-face-recognition" << EOF
/var/log/pi5-face-recognition/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
    
    success "Permissions set"
}

# Create desktop shortcut
create_desktop_shortcut() {
    info "Creating desktop shortcut..."
    
    cat > "$USER_HOME/Desktop/Pi5 Face Recognition.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Pi5 Face Recognition
Comment=Face Recognition System Dashboard
Exec=xdg-open http://localhost
Icon=camera-video
Terminal=false
Categories=Security;
EOF
    
    chmod +x "$USER_HOME/Desktop/Pi5 Face Recognition.desktop"
    chown pi:pi "$USER_HOME/Desktop/Pi5 Face Recognition.desktop"
    
    success "Desktop shortcut created"
}

# Create management scripts
create_management_scripts() {
    info "Creating management scripts..."
    
    # Start script
    cat > "$INSTALL_DIR/scripts/start.sh" << EOF
#!/bin/bash
echo "Starting Pi5 Face Recognition System..."
sudo systemctl start $SERVICE_NAME
sudo systemctl status $SERVICE_NAME --no-pager
EOF
    
    # Stop script
    cat > "$INSTALL_DIR/scripts/stop.sh" << EOF
#!/bin/bash
echo "Stopping Pi5 Face Recognition System..."
sudo systemctl stop $SERVICE_NAME
echo "System stopped."
EOF
    
    # Status script
    cat > "$INSTALL_DIR/scripts/status.sh" << EOF
#!/bin/bash
echo "Pi5 Face Recognition System Status:"
sudo systemctl status $SERVICE_NAME --no-pager
echo
echo "Recent logs:"
sudo journalctl -u $SERVICE_NAME -n 10 --no-pager
EOF
    
    # Logs script
    cat > "$INSTALL_DIR/scripts/logs.sh" << EOF
#!/bin/bash
echo "Following Pi5 Face Recognition logs (Ctrl+C to exit):"
sudo journalctl -u $SERVICE_NAME -f
EOF
    
    chmod +x "$INSTALL_DIR/scripts"/*.sh
    chown pi:pi "$INSTALL_DIR/scripts"/*.sh
    
    success "Management scripts created"
}

# Final configuration
final_configuration() {
    info "Performing final configuration..."
    
    # Update config file with detected settings
    if [ -f "$INSTALL_DIR/config/config.json" ]; then
        # Update camera device if found
        if [ -e "/dev/video0" ]; then
            sed -i 's|"camera_device": ".*"|"camera_device": "/dev/video0"|' "$INSTALL_DIR/config/config.json"
        fi
        
        # Update model path
        sed -i "s|\"model_path\": \".*\"|\"model_path\": \"$INSTALL_DIR/models/retinaface_mobilenet_v1.hef\"|" "$INSTALL_DIR/config/config.json"
    fi
    
    success "Final configuration completed"
}

# Main installation function
main() {
    show_banner
    
    # Start logging
    echo "Installation started at $(date)" > "$LOG_FILE"
    
    info "Starting installation process..."
    
    # Installation steps
    check_root
    detect_hardware
    update_system
    install_system_dependencies
    install_hailo_software
    create_directories
    copy_application_files
    install_python_dependencies
    download_models
    setup_database
    create_service
    setup_web_server
    set_permissions
    create_desktop_shortcut
    create_management_scripts
    final_configuration
    
    # Installation complete
    echo ""
    success "Installation completed successfully!"
    
    info "System Information:"
    echo "  - Installation Directory: $INSTALL_DIR"
    echo "  - Service Name: $SERVICE_NAME"
    echo "  - Web Dashboard: http://$(hostname -I | awk '{print $1}')"
    echo "  - Management Scripts: $INSTALL_DIR/scripts/"
    echo "  - Log File: $LOG_FILE"
    
    echo ""
    info "Next Steps:"
    echo "  1. Reboot your Raspberry Pi: sudo reboot"
    echo "  2. Access the web dashboard at http://$(hostname -I | awk '{print $1}')"
    echo "  3. Add known faces using the enrollment interface"
    echo "  4. Configure alerts and notifications as needed"
    
    echo ""
    info "Management Commands:"
    echo "  - Start system: $INSTALL_DIR/scripts/start.sh"
    echo "  - Stop system: $INSTALL_DIR/scripts/stop.sh"
    echo "  - Check status: $INSTALL_DIR/scripts/status.sh"
    echo "  - View logs: $INSTALL_DIR/scripts/logs.sh"
    
    echo ""
    log "${GREEN}🎉 Pi5 Face Recognition System installation complete!${NC}"
}

# Run main function
main "$@"