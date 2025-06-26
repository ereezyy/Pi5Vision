#!/bin/bash
# Installation validation script for Pi5 Face Recognition System
# Comprehensive testing and validation of the complete system

set -e

# Configuration
INSTALL_DIR="/opt/pi5-face-recognition"
SERVICE_NAME="pi5-face-recognition"
WEB_SERVICE_NAME="pi5-web-dashboard"
MONITOR_SERVICE_NAME="pi5-system-monitor"
WEB_PORT=8080

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNINGS=0

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_TESTS++))
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_TESTS++))
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

test_case() {
    ((TOTAL_TESTS++))
    echo -e "${BLUE}[TEST]${NC} $1"
}

# Test file system structure
test_file_structure() {
    log "Testing file system structure..."
    
    test_case "Installation directory exists"
    if [ -d "$INSTALL_DIR" ]; then
        success "Installation directory found: $INSTALL_DIR"
    else
        fail "Installation directory not found: $INSTALL_DIR"
        return 1
    fi
    
    # Required directories
    local required_dirs=(
        "src"
        "models" 
        "database"
        "alerts"
        "faces"
        "logs"
        "static"
        "templates"
        "config"
        "scripts"
        "venv"
    )
    
    for dir in "${required_dirs[@]}"; do
        test_case "Directory $dir exists"
        if [ -d "$INSTALL_DIR/$dir" ]; then
            success "Directory exists: $dir"
        else
            fail "Directory missing: $dir"
        fi
    done
    
    # Required files
    local required_files=(
        "src/database_manager.py"
        "src/model_manager.py"
        "src/enhanced_web_dashboard.py"
        "src/system_monitor.py"
        "src/production_config.py"
        "config/config.json"
        "scripts/start_all.sh"
        "scripts/health_check.sh"
    )
    
    for file in "${required_files[@]}"; do
        test_case "File $file exists"
        if [ -f "$INSTALL_DIR/$file" ]; then
            success "File exists: $file"
        else
            fail "File missing: $file"
        fi
    done
}

# Test Python environment
test_python_environment() {
    log "Testing Python environment..."
    
    test_case "Virtual environment exists"
    if [ -d "$INSTALL_DIR/venv" ]; then
        success "Virtual environment found"
    else
        fail "Virtual environment not found"
        return 1
    fi
    
    test_case "Python executable in venv"
    if [ -f "$INSTALL_DIR/venv/bin/python" ]; then
        success "Python executable found in venv"
    else
        fail "Python executable not found in venv"
        return 1
    fi
    
    # Test Python version
    test_case "Python version check"
    local python_version=$("$INSTALL_DIR/venv/bin/python" --version 2>&1 | awk '{print $2}')
    local major_version=$(echo $python_version | cut -d. -f1)
    local minor_version=$(echo $python_version | cut -d. -f2)
    
    if [ "$major_version" -eq 3 ] && [ "$minor_version" -ge 8 ]; then
        success "Python version is compatible: $python_version"
    else
        fail "Python version is too old: $python_version (requires 3.8+)"
    fi
    
    # Test required Python packages
    local required_packages=(
        "fastapi"
        "uvicorn"
        "pydantic"
        "sqlite3"
        "numpy"
        "pillow"
    )
    
    for package in "${required_packages[@]}"; do
        test_case "Python package: $package"
        if "$INSTALL_DIR/venv/bin/python" -c "import $package" 2>/dev/null; then
            success "Package available: $package"
        else
            fail "Package missing: $package"
        fi
    done
}

# Test database functionality
test_database() {
    log "Testing database functionality..."
    
    test_case "Database manager import"
    if cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "from src.database_manager import DatabaseManager" 2>/dev/null; then
        success "Database manager imports successfully"
    else
        fail "Database manager import failed"
        return 1
    fi
    
    test_case "Database initialization"
    if cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "
from src.database_manager import DatabaseManager
db = DatabaseManager('$INSTALL_DIR/database/test.db')
result = db.initialize_database()
print('SUCCESS' if result else 'FAILED')
" | grep -q "SUCCESS"; then
        success "Database initializes successfully"
    else
        fail "Database initialization failed"
    fi
    
    test_case "Database operations"
    if cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "
from src.database_manager import DatabaseManager
db = DatabaseManager('$INSTALL_DIR/database/test.db')
db.initialize_database()
person_id = db.add_person('Test Person', 'Test notes')
person = db.get_person(person_id) if person_id else None
print('SUCCESS' if person and person['name'] == 'Test Person' else 'FAILED')
" | grep -q "SUCCESS"; then
        success "Database operations work correctly"
    else
        fail "Database operations failed"
    fi
    
    # Clean up test database
    rm -f "$INSTALL_DIR/database/test.db"
}

# Test model manager
test_model_manager() {
    log "Testing model manager..."
    
    test_case "Model manager import"
    if cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "from src.model_manager import HailoModelManager" 2>/dev/null; then
        success "Model manager imports successfully"
    else
        fail "Model manager import failed"
        return 1
    fi
    
    test_case "Model validation"
    if cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "
from src.model_manager import HailoModelManager
manager = HailoModelManager('$INSTALL_DIR/models')
report = manager.validate_models()
print('SUCCESS' if 'total_models' in report else 'FAILED')
" | grep -q "SUCCESS"; then
        success "Model validation works"
    else
        fail "Model validation failed"
    fi
    
    test_case "Model download simulation"
    if cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "
from src.model_manager import HailoModelManager
manager = HailoModelManager('$INSTALL_DIR/models')
results = manager.download_missing_models()
print('SUCCESS' if isinstance(results, dict) else 'FAILED')
" | grep -q "SUCCESS"; then
        success "Model download works"
    else
        fail "Model download failed"
    fi
}

# Test web dashboard
test_web_dashboard() {
    log "Testing web dashboard..."
    
    test_case "Web dashboard import"
    if cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "from src.enhanced_web_dashboard import EnhancedWebDashboard" 2>/dev/null; then
        success "Web dashboard imports successfully"
    else
        fail "Web dashboard import failed"
        return 1
    fi
    
    test_case "FastAPI app creation"
    if cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "
from src.enhanced_web_dashboard import EnhancedWebDashboard
dashboard = EnhancedWebDashboard()
print('SUCCESS' if hasattr(dashboard, 'app') else 'FAILED')
" | grep -q "SUCCESS"; then
        success "FastAPI app creates successfully"
    else
        fail "FastAPI app creation failed"
    fi
}

# Test system monitor
test_system_monitor() {
    log "Testing system monitor..."
    
    test_case "System monitor import"
    if cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "from src.system_monitor import SystemMonitor" 2>/dev/null; then
        success "System monitor imports successfully"
    else
        fail "System monitor import failed"
        return 1
    fi
    
    test_case "Metrics collection"
    if cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "
from src.system_monitor import SystemMonitor
monitor = SystemMonitor()
metrics = monitor._collect_metrics()
print('SUCCESS' if hasattr(metrics, 'cpu_percent') else 'FAILED')
" | grep -q "SUCCESS"; then
        success "Metrics collection works"
    else
        fail "Metrics collection failed"
    fi
}

# Test hardware detection
test_hardware() {
    log "Testing hardware detection..."
    
    test_case "Raspberry Pi detection"
    if grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        success "Running on Raspberry Pi"
        
        test_case "Raspberry Pi 5 detection"
        if grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
            success "Running on Raspberry Pi 5"
        else
            warning "Not running on Raspberry Pi 5"
        fi
    else
        warning "Not running on Raspberry Pi hardware"
    fi
    
    test_case "Hailo device detection"
    if lspci 2>/dev/null | grep -i hailo >/dev/null; then
        success "Hailo device detected"
    else
        warning "Hailo device not detected"
    fi
    
    test_case "Camera detection"
    if ls /dev/video* >/dev/null 2>&1; then
        local camera_count=$(ls /dev/video* | wc -l)
        success "Found $camera_count camera device(s)"
    else
        warning "No camera devices found"
    fi
    
    test_case "USB devices"
    if lsusb >/dev/null 2>&1; then
        local usb_count=$(lsusb | wc -l)
        success "Found $usb_count USB devices"
    else
        warning "Could not enumerate USB devices"
    fi
}

# Test system services
test_services() {
    log "Testing system services..."
    
    local services=("$SERVICE_NAME" "$WEB_SERVICE_NAME" "$MONITOR_SERVICE_NAME")
    
    for service in "${services[@]}"; do
        test_case "Service file exists: $service"
        if [ -f "/etc/systemd/system/${service}.service" ]; then
            success "Service file exists: $service"
        else
            fail "Service file missing: $service"
        fi
        
        test_case "Service is enabled: $service"
        if systemctl is-enabled "$service" >/dev/null 2>&1; then
            success "Service is enabled: $service"
        else
            warning "Service is not enabled: $service"
        fi
        
        test_case "Service status: $service"
        if systemctl is-active "$service" >/dev/null 2>&1; then
            success "Service is running: $service"
        else
            warning "Service is not running: $service"
        fi
    done
}

# Test web interface
test_web_interface() {
    log "Testing web interface..."
    
    test_case "Web server port availability"
    if netstat -tuln 2>/dev/null | grep ":$WEB_PORT " >/dev/null; then
        success "Web server is listening on port $WEB_PORT"
        
        test_case "Web interface response"
        if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$WEB_PORT" | grep -q "200"; then
            success "Web interface responds successfully"
        else
            fail "Web interface not responding"
        fi
    else
        warning "Web server not listening on port $WEB_PORT"
    fi
}

# Test system resources
test_system_resources() {
    log "Testing system resources..."
    
    test_case "Available memory"
    local mem_total=$(free -m | awk 'NR==2{print $2}')
    if [ "$mem_total" -ge 1024 ]; then
        success "Sufficient memory available: ${mem_total}MB"
    else
        warning "Low memory: ${mem_total}MB (recommended: 1GB+)"
    fi
    
    test_case "Available disk space"
    local disk_avail=$(df / | tail -1 | awk '{print $4}')
    local disk_avail_gb=$((disk_avail / 1024 / 1024))
    if [ "$disk_avail_gb" -ge 5 ]; then
        success "Sufficient disk space: ${disk_avail_gb}GB available"
    else
        warning "Low disk space: ${disk_avail_gb}GB available (recommended: 5GB+)"
    fi
    
    test_case "CPU temperature"
    if [ -f "/sys/class/thermal/thermal_zone0/temp" ]; then
        local temp=$(cat /sys/class/thermal/thermal_zone0/temp)
        local temp_celsius=$((temp / 1000))
        if [ "$temp_celsius" -lt 70 ]; then
            success "CPU temperature normal: ${temp_celsius}°C"
        else
            warning "CPU temperature high: ${temp_celsius}°C"
        fi
    else
        warning "Cannot read CPU temperature"
    fi
}

# Test configuration
test_configuration() {
    log "Testing configuration..."
    
    test_case "Configuration file exists"
    if [ -f "$INSTALL_DIR/config/config.json" ]; then
        success "Configuration file found"
        
        test_case "Configuration file is valid JSON"
        if python3 -m json.tool "$INSTALL_DIR/config/config.json" >/dev/null 2>&1; then
            success "Configuration file is valid JSON"
        else
            fail "Configuration file is invalid JSON"
        fi
    else
        fail "Configuration file not found"
    fi
    
    test_case "Log directory permissions"
    if [ -w "/var/log/pi5-face-recognition" ]; then
        success "Log directory is writable"
    else
        fail "Log directory is not writable"
    fi
}

# Test security
test_security() {
    log "Testing security configuration..."
    
    test_case "Service user permissions"
    if id pi >/dev/null 2>&1; then
        success "Service user 'pi' exists"
        
        test_case "Installation directory ownership"
        local owner=$(stat -c '%U' "$INSTALL_DIR")
        if [ "$owner" = "pi" ]; then
            success "Installation directory owned by 'pi'"
        else
            warning "Installation directory owned by '$owner' (expected: pi)"
        fi
    else
        fail "Service user 'pi' does not exist"
    fi
    
    test_case "Service security settings"
    if grep -q "NoNewPrivileges=true" "/etc/systemd/system/${SERVICE_NAME}.service" 2>/dev/null; then
        success "Service has security restrictions enabled"
    else
        warning "Service security restrictions not found"
    fi
}

# Generate validation report
generate_report() {
    echo
    echo "=============================================="
    echo "VALIDATION REPORT"
    echo "=============================================="
    echo "Total tests: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $FAILED_TESTS"
    echo "Warnings: $WARNINGS"
    echo
    
    local pass_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    
    if [ "$FAILED_TESTS" -eq 0 ]; then
        if [ "$WARNINGS" -eq 0 ]; then
            echo -e "${GREEN}✓ ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION${NC}"
        else
            echo -e "${YELLOW}⚠ ALL TESTS PASSED WITH $WARNINGS WARNING(S)${NC}"
        fi
    else
        echo -e "${RED}✗ $FAILED_TESTS TEST(S) FAILED - SYSTEM NOT READY${NC}"
    fi
    
    echo
    echo "Pass rate: ${pass_rate}%"
    echo
    
    if [ "$FAILED_TESTS" -gt 0 ]; then
        echo "Next steps:"
        echo "1. Review failed tests above"
        echo "2. Fix identified issues"
        echo "3. Re-run validation: $0"
        echo "4. Check logs for more details"
        echo
        return 1
    else
        echo "System validation successful!"
        echo "You can now start the system with:"
        echo "  $INSTALL_DIR/scripts/start_all.sh"
        echo
        echo "Access the web dashboard at:"
        echo "  http://$(hostname -I | awk '{print $1}'):$WEB_PORT"
        echo
        return 0
    fi
}

# Main validation function
main() {
    echo "Pi5 Face Recognition System - Installation Validation"
    echo "======================================================"
    echo "Starting comprehensive system validation..."
    echo
    
    # Run all test suites
    test_file_structure
    test_python_environment
    test_database
    test_model_manager
    test_web_dashboard
    test_system_monitor
    test_hardware
    test_services
    test_web_interface
    test_system_resources
    test_configuration
    test_security
    
    # Generate final report
    generate_report
}

# Run validation
main "$@"