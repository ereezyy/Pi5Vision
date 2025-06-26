#!/bin/bash
# Deployment script for Pi5 Face Recognition System
# Handles packaging, distribution, and remote deployment

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="pi5-face-recognition"
VERSION="2.0.0"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"
PACKAGE_NAME="${PROJECT_NAME}-${VERSION}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
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

# Show banner
show_banner() {
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}    Pi5 Face Recognition System - Deployment Tool v${VERSION}${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
}

# Clean build directories
clean_build() {
    log "Cleaning build directories..."
    rm -rf "$BUILD_DIR" "$DIST_DIR"
    mkdir -p "$BUILD_DIR" "$DIST_DIR"
    success "Build directories cleaned"
}

# Create deployment package
create_package() {
    log "Creating deployment package..."
    
    PACKAGE_DIR="$BUILD_DIR/$PACKAGE_NAME"
    mkdir -p "$PACKAGE_DIR"
    
    # Copy source files
    log "Copying source files..."
    cp -r src "$PACKAGE_DIR/"
    cp -r templates "$PACKAGE_DIR/" 2>/dev/null || warning "Templates directory not found"
    cp -r static "$PACKAGE_DIR/" 2>/dev/null || warning "Static directory not found"
    
    # Copy configuration and documentation
    log "Copying configuration and documentation..."
    cp config.json "$PACKAGE_DIR/" 2>/dev/null || warning "config.json not found"
    cp requirements.txt "$PACKAGE_DIR/" 2>/dev/null || warning "requirements.txt not found"
    cp *.md "$PACKAGE_DIR/" 2>/dev/null || warning "Documentation files not found"
    cp LICENSE "$PACKAGE_DIR/" 2>/dev/null || warning "LICENSE file not found"
    
    # Copy installation scripts
    log "Copying installation scripts..."
    cp install_pi5.sh "$PACKAGE_DIR/"
    chmod +x "$PACKAGE_DIR/install_pi5.sh"
    
    # Create deployment-specific files
    log "Creating deployment files..."
    
    # Create version file
    cat > "$PACKAGE_DIR/VERSION" << EOF
Pi5 Face Recognition System
Version: $VERSION
Build Date: $(date)
Build Host: $(hostname)
Git Commit: $(git rev-parse HEAD 2>/dev/null || echo "unknown")
EOF
    
    # Create deployment script
    cat > "$PACKAGE_DIR/deploy.sh" << 'EOF'
#!/bin/bash
# Local deployment script
set -e

echo "Pi5 Face Recognition System - Local Deployment"
echo "================================================"

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "WARNING: Not running on Raspberry Pi hardware"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled"
        exit 1
    fi
fi

# Run installation
echo "Starting installation..."
sudo ./install_pi5.sh

echo
echo "Deployment completed!"
echo "Access the system at: http://$(hostname -I | awk '{print $1}')"
EOF
    
    chmod +x "$PACKAGE_DIR/deploy.sh"
    
    # Create quick start guide
    cat > "$PACKAGE_DIR/QUICK_START.md" << EOF
# Quick Start Guide

## Hardware Requirements
- Raspberry Pi 5 (4GB+ RAM recommended)
- Hailo AI HAT+ (26 TOPS)
- USB Camera (1080p recommended)
- MicroSD card (32GB+ Class 10)

## Installation Steps

1. **Flash Raspberry Pi OS**
   - Use Raspberry Pi Imager
   - Flash Raspberry Pi OS Bookworm (64-bit)
   - Enable SSH and configure Wi-Fi if needed

2. **Install Hailo AI HAT+**
   - Power off the Raspberry Pi
   - Carefully attach the Hailo AI HAT+
   - Power on and verify detection: \`lspci | grep Hailo\`

3. **Deploy the System**
   \`\`\`bash
   chmod +x deploy.sh
   ./deploy.sh
   \`\`\`

4. **Access the Dashboard**
   - Open browser: http://your-pi-ip-address
   - Default login: admin/admin (change immediately)

## Quick Commands
- Start system: \`sudo systemctl start pi5-face-recognition\`
- Stop system: \`sudo systemctl stop pi5-face-recognition\`
- View logs: \`sudo journalctl -u pi5-face-recognition -f\`
- System status: \`sudo systemctl status pi5-face-recognition\`

## Troubleshooting
- Check installation log: \`/tmp/pi5_install.log\`
- Verify camera: \`ls /dev/video*\`
- Test Hailo: \`hailortcli fw-control identify\`

For detailed documentation, see README.md
EOF
    
    success "Package structure created"
}

# Create compressed archive
create_archive() {
    log "Creating compressed archive..."
    
    cd "$BUILD_DIR"
    
    # Create tar.gz archive
    tar -czf "$DIST_DIR/${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
    
    # Create zip archive for Windows users
    if command -v zip >/dev/null 2>&1; then
        zip -r "$DIST_DIR/${PACKAGE_NAME}.zip" "$PACKAGE_NAME" >/dev/null
        success "Created zip archive: ${PACKAGE_NAME}.zip"
    fi
    
    success "Created tar.gz archive: ${PACKAGE_NAME}.tar.gz"
    
    cd "$SCRIPT_DIR"
}

# Generate checksums
generate_checksums() {
    log "Generating checksums..."
    
    cd "$DIST_DIR"
    
    # Generate SHA256 checksums
    sha256sum *.tar.gz *.zip 2>/dev/null > checksums.sha256 || true
    
    success "Checksums generated"
    
    cd "$SCRIPT_DIR"
}

# Deploy to remote Pi
deploy_remote() {
    local PI_HOST="$1"
    local PI_USER="${2:-pi}"
    
    if [ -z "$PI_HOST" ]; then
        error "Remote host not specified"
    fi
    
    log "Deploying to remote Raspberry Pi: $PI_USER@$PI_HOST"
    
    # Check if we can connect
    if ! ssh -q -o ConnectTimeout=5 "$PI_USER@$PI_HOST" exit; then
        error "Cannot connect to $PI_USER@$PI_HOST"
    fi
    
    # Copy package to remote Pi
    log "Copying package to remote Pi..."
    scp "$DIST_DIR/${PACKAGE_NAME}.tar.gz" "$PI_USER@$PI_HOST:/tmp/"
    
    # Extract and deploy on remote Pi
    log "Extracting and deploying on remote Pi..."
    ssh "$PI_USER@$PI_HOST" << EOF
set -e
cd /tmp
tar -xzf ${PACKAGE_NAME}.tar.gz
cd ${PACKAGE_NAME}
chmod +x deploy.sh
./deploy.sh
EOF
    
    success "Remote deployment completed"
    log "System should be available at: http://$PI_HOST"
}

# Create Docker image (for development/testing)
create_docker_image() {
    log "Creating Docker image for development..."
    
    # Create Dockerfile
    cat > "$BUILD_DIR/Dockerfile" << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libjpeg-dev \
    libtiff5-dev \
    libpng-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libfontconfig1-dev \
    libcairo2-dev \
    libgdk-pixbuf2.0-dev \
    libpango1.0-dev \
    libgtk2.0-dev \
    libatlas-base-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY pi5-face-recognition/ /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Start command
CMD ["python", "src/web_dashboard.py"]
EOF
    
    # Build Docker image
    if command -v docker >/dev/null 2>&1; then
        cd "$BUILD_DIR"
        docker build -t "pi5-face-recognition:$VERSION" .
        docker tag "pi5-face-recognition:$VERSION" "pi5-face-recognition:latest"
        success "Docker image created: pi5-face-recognition:$VERSION"
        cd "$SCRIPT_DIR"
    else
        warning "Docker not found, skipping Docker image creation"
    fi
}

# Show package information
show_package_info() {
    log "Package Information:"
    echo "  Name: $PACKAGE_NAME"
    echo "  Version: $VERSION"
    echo "  Build Directory: $BUILD_DIR"
    echo "  Distribution Directory: $DIST_DIR"
    echo ""
    
    if [ -d "$DIST_DIR" ]; then
        log "Distribution Files:"
        ls -lh "$DIST_DIR"
        echo ""
        
        if [ -f "$DIST_DIR/checksums.sha256" ]; then
            log "Checksums:"
            cat "$DIST_DIR/checksums.sha256"
            echo ""
        fi
    fi
}

# Main deployment function
main() {
    show_banner
    
    case "${1:-package}" in
        "clean")
            clean_build
            ;;
        "package")
            clean_build
            create_package
            create_archive
            generate_checksums
            show_package_info
            ;;
        "docker")
            clean_build
            create_package
            create_docker_image
            ;;
        "remote")
            if [ -z "$2" ]; then
                error "Usage: $0 remote <pi-hostname-or-ip> [username]"
            fi
            
            # Create package if it doesn't exist
            if [ ! -f "$DIST_DIR/${PACKAGE_NAME}.tar.gz" ]; then
                log "Package not found, creating..."
                clean_build
                create_package
                create_archive
            fi
            
            deploy_remote "$2" "$3"
            ;;
        "info")
            show_package_info
            ;;
        "help"|"--help"|"-h")
            echo "Pi5 Face Recognition Deployment Tool"
            echo ""
            echo "Usage: $0 [command] [options]"
            echo ""
            echo "Commands:"
            echo "  package                Create deployment package (default)"
            echo "  docker                 Create Docker image for development"
            echo "  remote <host> [user]   Deploy to remote Raspberry Pi"
            echo "  clean                  Clean build directories"
            echo "  info                   Show package information"
            echo "  help                   Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 package                    # Create deployment package"
            echo "  $0 remote raspberrypi.local   # Deploy to Pi at raspberrypi.local"
            echo "  $0 remote 192.168.1.100 pi    # Deploy to Pi at IP with user 'pi'"
            echo "  $0 docker                     # Create Docker image"
            ;;
        *)
            error "Unknown command: $1. Use '$0 help' for usage information."
            ;;
    esac
}

# Run main function with all arguments
main "$@"