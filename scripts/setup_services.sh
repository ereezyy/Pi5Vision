#!/bin/bash
# Service setup script for Pi5 Face Recognition System
# Creates and configures systemd services

set -e

# Configuration
SERVICE_NAME="pi5-face-recognition"
WEB_SERVICE_NAME="pi5-web-dashboard"
MONITOR_SERVICE_NAME="pi5-system-monitor"
INSTALL_DIR="/opt/pi5-face-recognition"
USER="pi"
GROUP="pi"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
fi

# Create main face recognition service
create_main_service() {
    log "Creating main face recognition service..."
    
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Pi5 Face Recognition System
Documentation=https://github.com/pi5vision/face-recognition
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$INSTALL_DIR/src
Environment=PYTHONUNBUFFERED=1
ExecStartPre=/bin/sleep 10
ExecStart=$INSTALL_DIR/venv/bin/python -m face_tracking --config config/config.json
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
TimeoutStartSec=60
TimeoutStopSec=30

# Resource limits
MemoryLimit=1G
CPUQuota=80%

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR
CapabilityBoundingSet=CAP_NET_BIND_SERVICE

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

    success "Main service created"
}

# Create web dashboard service
create_web_service() {
    log "Creating web dashboard service..."
    
    cat > "/etc/systemd/system/${WEB_SERVICE_NAME}.service" << EOF
[Unit]
Description=Pi5 Face Recognition Web Dashboard
Documentation=https://github.com/pi5vision/face-recognition
After=network.target ${SERVICE_NAME}.service
Wants=network.target
BindsTo=${SERVICE_NAME}.service

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$INSTALL_DIR/src
Environment=PYTHONUNBUFFERED=1
ExecStart=$INSTALL_DIR/venv/bin/python -m enhanced_web_dashboard --host 0.0.0.0 --port 8080
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
TimeoutStartSec=30
TimeoutStopSec=15

# Resource limits
MemoryLimit=512M
CPUQuota=50%

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$WEB_SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

    success "Web dashboard service created"
}

# Create system monitor service
create_monitor_service() {
    log "Creating system monitor service..."
    
    cat > "/etc/systemd/system/${MONITOR_SERVICE_NAME}.service" << EOF
[Unit]
Description=Pi5 Face Recognition System Monitor
Documentation=https://github.com/pi5vision/face-recognition
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$INSTALL_DIR/src
Environment=PYTHONUNBUFFERED=1
ExecStart=$INSTALL_DIR/venv/bin/python -m system_monitor
Restart=always
RestartSec=15
TimeoutStartSec=30
TimeoutStopSec=15

# Resource limits
MemoryLimit=256M
CPUQuota=20%

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$MONITOR_SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

    success "System monitor service created"
}

# Create service management scripts
create_management_scripts() {
    log "Creating service management scripts..."
    
    mkdir -p "$INSTALL_DIR/scripts"
    
    # Start all services script
    cat > "$INSTALL_DIR/scripts/start_all.sh" << EOF
#!/bin/bash
echo "Starting Pi5 Face Recognition System..."
sudo systemctl start $SERVICE_NAME
sudo systemctl start $WEB_SERVICE_NAME  
sudo systemctl start $MONITOR_SERVICE_NAME
echo "All services started"
sudo systemctl status $SERVICE_NAME --no-pager -l
EOF

    # Stop all services script
    cat > "$INSTALL_DIR/scripts/stop_all.sh" << EOF
#!/bin/bash
echo "Stopping Pi5 Face Recognition System..."
sudo systemctl stop $SERVICE_NAME
sudo systemctl stop $WEB_SERVICE_NAME
sudo systemctl stop $MONITOR_SERVICE_NAME
echo "All services stopped"
EOF

    # Status script
    cat > "$INSTALL_DIR/scripts/status_all.sh" << EOF
#!/bin/bash
echo "Pi5 Face Recognition System Status:"
echo "=================================="
echo
echo "Main Service:"
sudo systemctl status $SERVICE_NAME --no-pager -l
echo
echo "Web Dashboard:"
sudo systemctl status $WEB_SERVICE_NAME --no-pager -l
echo
echo "System Monitor:"
sudo systemctl status $MONITOR_SERVICE_NAME --no-pager -l
EOF

    # Restart script
    cat > "$INSTALL_DIR/scripts/restart_all.sh" << EOF
#!/bin/bash
echo "Restarting Pi5 Face Recognition System..."
sudo systemctl restart $SERVICE_NAME
sudo systemctl restart $WEB_SERVICE_NAME
sudo systemctl restart $MONITOR_SERVICE_NAME
echo "All services restarted"
EOF

    # Logs script
    cat > "$INSTALL_DIR/scripts/logs_all.sh" << EOF
#!/bin/bash
echo "Following Pi5 Face Recognition logs (Ctrl+C to exit):"
sudo journalctl -f -u $SERVICE_NAME -u $WEB_SERVICE_NAME -u $MONITOR_SERVICE_NAME
EOF

    # Enable services script
    cat > "$INSTALL_DIR/scripts/enable_all.sh" << EOF
#!/bin/bash
echo "Enabling Pi5 Face Recognition services for auto-start..."
sudo systemctl enable $SERVICE_NAME
sudo systemctl enable $WEB_SERVICE_NAME
sudo systemctl enable $MONITOR_SERVICE_NAME
echo "All services enabled for auto-start"
EOF

    # Disable services script
    cat > "$INSTALL_DIR/scripts/disable_all.sh" << EOF
#!/bin/bash
echo "Disabling Pi5 Face Recognition services from auto-start..."
sudo systemctl disable $SERVICE_NAME
sudo systemctl disable $WEB_SERVICE_NAME
sudo systemctl disable $MONITOR_SERVICE_NAME
echo "All services disabled from auto-start"
EOF

    # Make scripts executable
    chmod +x "$INSTALL_DIR/scripts"/*.sh
    chown $USER:$GROUP "$INSTALL_DIR/scripts"/*.sh
    
    success "Management scripts created"
}

# Create logrotate configuration
create_logrotate_config() {
    log "Creating logrotate configuration..."
    
    cat > "/etc/logrotate.d/pi5-face-recognition" << EOF
# Pi5 Face Recognition System log rotation
/var/log/pi5-face-recognition/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    copytruncate
    create 644 $USER $GROUP
    postrotate
        systemctl reload $SERVICE_NAME > /dev/null 2>&1 || true
        systemctl reload $WEB_SERVICE_NAME > /dev/null 2>&1 || true
        systemctl reload $MONITOR_SERVICE_NAME > /dev/null 2>&1 || true
    endscript
}

# Journal logs for systemd services
/var/log/journal/*/*.journal {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

    success "Logrotate configuration created"
}

# Create monitoring script
create_monitoring_script() {
    log "Creating health monitoring script..."
    
    cat > "$INSTALL_DIR/scripts/health_check.sh" << EOF
#!/bin/bash
# Health check script for Pi5 Face Recognition System

# Configuration
MAIN_SERVICE="$SERVICE_NAME"
WEB_SERVICE="$WEB_SERVICE_NAME"
MONITOR_SERVICE="$MONITOR_SERVICE_NAME"
WEB_PORT=8080
CHECK_INTERVAL=60

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local service=\$1
    if systemctl is-active --quiet \$service; then
        echo -e "\${GREEN}✓\${NC} \$service is running"
        return 0
    else
        echo -e "\${RED}✗\${NC} \$service is not running"
        return 1
    fi
}

check_web_interface() {
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:\$WEB_PORT | grep -q "200"; then
        echo -e "\${GREEN}✓\${NC} Web interface is responding"
        return 0
    else
        echo -e "\${RED}✗\${NC} Web interface is not responding"
        return 1
    fi
}

check_system_resources() {
    local cpu_usage=\$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | awk -F'%' '{print \$1}')
    local mem_usage=\$(free | grep Mem | awk '{printf("%.1f", \$3/\$2 * 100.0)}')
    local disk_usage=\$(df / | tail -1 | awk '{print \$5}' | sed 's/%//')
    
    echo "System Resources:"
    echo "  CPU Usage: \${cpu_usage}%"
    echo "  Memory Usage: \${mem_usage}%"
    echo "  Disk Usage: \${disk_usage}%"
    
    # Check thresholds
    if (( \$(echo "\$cpu_usage > 90" | bc -l) )); then
        echo -e "\${YELLOW}⚠\${NC} High CPU usage detected"
    fi
    
    if (( \$(echo "\$mem_usage > 90" | bc -l) )); then
        echo -e "\${YELLOW}⚠\${NC} High memory usage detected"
    fi
    
    if [ \$disk_usage -gt 90 ]; then
        echo -e "\${YELLOW}⚠\${NC} High disk usage detected"
    fi
}

main() {
    echo "Pi5 Face Recognition Health Check - \$(date)"
    echo "==========================================="
    
    local issues=0
    
    # Check services
    echo "Checking services..."
    check_service \$MAIN_SERVICE || ((issues++))
    check_service \$WEB_SERVICE || ((issues++))
    check_service \$MONITOR_SERVICE || ((issues++))
    
    echo
    
    # Check web interface
    echo "Checking web interface..."
    check_web_interface || ((issues++))
    
    echo
    
    # Check system resources
    check_system_resources
    
    echo
    
    if [ \$issues -eq 0 ]; then
        echo -e "\${GREEN}✓ All checks passed\${NC}"
        exit 0
    else
        echo -e "\${RED}✗ \$issues issue(s) detected\${NC}"
        exit 1
    fi
}

# Run health check
main "\$@"
EOF

    chmod +x "$INSTALL_DIR/scripts/health_check.sh"
    chown $USER:$GROUP "$INSTALL_DIR/scripts/health_check.sh"
    
    success "Health monitoring script created"
}

# Create cron jobs
setup_cron_jobs() {
    log "Setting up cron jobs..."
    
    # Create cron job for health checks
    cat > "/etc/cron.d/pi5-face-recognition" << EOF
# Pi5 Face Recognition System maintenance

# Health check every 5 minutes
*/5 * * * * $USER $INSTALL_DIR/scripts/health_check.sh >> /var/log/pi5-face-recognition/health.log 2>&1

# Database cleanup daily at 2 AM
0 2 * * * $USER cd $INSTALL_DIR && $INSTALL_DIR/venv/bin/python -c "from src.database_manager import DatabaseManager; db = DatabaseManager(); db.cleanup_old_data()" >> /var/log/pi5-face-recognition/cleanup.log 2>&1

# Log rotation check daily at 3 AM
0 3 * * * root /usr/sbin/logrotate /etc/logrotate.d/pi5-face-recognition

# System restart weekly on Sunday at 3 AM (optional)
# 0 3 * * 0 root systemctl restart $SERVICE_NAME $WEB_SERVICE_NAME $MONITOR_SERVICE_NAME
EOF

    success "Cron jobs configured"
}

# Main installation
main() {
    echo "Pi5 Face Recognition System - Service Setup"
    echo "============================================"
    
    # Create log directory
    mkdir -p "/var/log/pi5-face-recognition"
    chown $USER:$GROUP "/var/log/pi5-face-recognition"
    
    # Create services
    create_main_service
    create_web_service
    create_monitor_service
    
    # Create management scripts
    create_management_scripts
    
    # Create logrotate config
    create_logrotate_config
    
    # Create monitoring
    create_monitoring_script
    
    # Setup cron jobs
    setup_cron_jobs
    
    # Reload systemd
    log "Reloading systemd daemon..."
    systemctl daemon-reload
    
    # Enable services
    log "Enabling services..."
    systemctl enable $SERVICE_NAME
    systemctl enable $WEB_SERVICE_NAME
    systemctl enable $MONITOR_SERVICE_NAME
    
    echo
    success "Service setup completed successfully!"
    
    echo
    log "Available commands:"
    echo "  Start all:    $INSTALL_DIR/scripts/start_all.sh"
    echo "  Stop all:     $INSTALL_DIR/scripts/stop_all.sh"
    echo "  Status:       $INSTALL_DIR/scripts/status_all.sh"
    echo "  Restart all:  $INSTALL_DIR/scripts/restart_all.sh"
    echo "  View logs:    $INSTALL_DIR/scripts/logs_all.sh"
    echo "  Health check: $INSTALL_DIR/scripts/health_check.sh"
    
    echo
    log "To start the system now:"
    echo "  $INSTALL_DIR/scripts/start_all.sh"
}

# Run main function
main "$@"