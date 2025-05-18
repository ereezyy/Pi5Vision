# Raspberry Pi 5 Face Recognition System with Hailo AI HAT+

## User Manual

### Overview

This system provides a modern, real-time face recognition solution for your Raspberry Pi 5 with the Hailo AI HAT+ accelerator. It uses your USB camera to detect and recognize faces, track visitors, and alert you when new faces are detected.

### Features

- Real-time face detection and recognition using the Hailo AI accelerator
- Face tracking across video frames
- Database storage of known faces
- Automatic alerts for new or unknown faces
- Easy installation and configuration
- Runs as a system service for 24/7 operation

### Hardware Requirements

- Raspberry Pi 5 (any RAM configuration, 4GB+ recommended)
- Hailo AI HAT+ (26 TOPS model)
- USB camera (720p or higher resolution recommended)
- MicroSD card (16GB+ recommended)
- Power supply for Raspberry Pi 5 (5V/5A recommended)

### Software Requirements

- Raspberry Pi OS Bookworm (64-bit recommended)
- Internet connection for installation

### Installation

1. **Prepare your Raspberry Pi**
   - Install Raspberry Pi OS Bookworm on your Pi 5
   - Ensure your Pi is connected to the internet
   - Connect your USB camera

2. **Install the Hailo AI HAT+**
   - Power off your Raspberry Pi
   - Carefully attach the Hailo AI HAT+ to the GPIO pins
   - Secure the HAT with standoffs if available
   - Power on your Raspberry Pi

3. **Download the installation package**
   - Download the face recognition package from the provided link
   - Extract the package to a directory on your Pi

4. **Run the installation script**
   - Open a terminal and navigate to the extracted directory
   - Run the installation script with sudo:
     ```
     sudo bash install.sh
     ```
   - Follow the on-screen prompts
   - The installation will take 10-15 minutes to complete

5. **Reboot your Raspberry Pi**
   - After installation completes, reboot your Pi:
     ```
     sudo reboot
     ```

### Using the System

#### Automatic Operation

After installation, the face recognition system will start automatically when your Raspberry Pi boots up. It will:

- Initialize the camera and Hailo accelerator
- Begin detecting and recognizing faces
- Generate alerts for unknown faces
- Store data in the database

#### Manual Operation

You can also start, stop, or check the status of the system manually:

- **Start the system**:
  ```
  sudo systemctl start face-recognition
  ```

- **Stop the system**:
  ```
  sudo systemctl stop face-recognition
  ```

- **Check status**:
  ```
  sudo systemctl status face-recognition
  ```

- **View logs**:
  ```
  sudo journalctl -u face-recognition -f
  ```

#### Desktop Shortcut

A desktop shortcut is created during installation. You can click this shortcut to start the face recognition system with a graphical interface.

### Configuration

The system can be configured by editing the `config.json` file located at `/opt/pi5-face-recognition/config.json`. After making changes, restart the service for them to take effect.

Key configuration options:

- `camera_device`: Path to your USB camera (default: `/dev/video0`)
- `resolution`: Camera resolution [width, height] (default: [1280, 720])
- `fps`: Camera frames per second (default: 30)
- `confidence_threshold`: Minimum confidence for face detection (default: 0.5)
- `similarity_threshold`: Threshold for face recognition (default: 0.6)
- `alert_settings`: Configure alert behavior
- `web_interface`: Enable/disable web interface (experimental)

### Adding Known Faces

To add known faces to the system:

1. Stop the face recognition service:
   ```
   sudo systemctl stop face-recognition
   ```

2. Run the face enrollment script:
   ```
   cd /opt/pi5-face-recognition
   sudo python3 face_enrollment.py
   ```

3. Follow the on-screen instructions to capture and name faces

4. Restart the face recognition service:
   ```
   sudo systemctl start face-recognition
   ```

### Alert Management

Alerts are stored in the `/opt/pi5-face-recognition/alerts` directory, with images of detected unknown faces. The system keeps a log of all alerts in the database.

### Troubleshooting

#### Camera Not Detected

- Ensure your USB camera is properly connected
- Check if the camera is recognized by the system:
  ```
  ls -l /dev/video*
  ```
- Try a different USB port
- Update the camera device in the configuration file

#### Hailo HAT Not Detected

- Ensure the HAT is properly seated on the GPIO pins
- Check if the HAT is recognized:
  ```
  sudo lspci | grep Hailo
  ```
- Verify the Hailo drivers are installed:
  ```
  hailortcli fw-control identify
  ```

#### System Not Starting

- Check the system logs:
  ```
  sudo journalctl -u face-recognition -e
  ```
- Verify all dependencies are installed:
  ```
  cd /opt/pi5-face-recognition
  pip3 install -r requirements.txt
  ```

#### Poor Recognition Performance

- Ensure good lighting conditions
- Adjust the confidence and similarity thresholds in the configuration
- Re-enroll faces with multiple angles and lighting conditions

### Maintenance

- **Database Backup**: The system automatically backs up the face database daily
- **Log Rotation**: Logs are automatically rotated to prevent disk space issues
- **Updates**: Check for system updates periodically

### Uninstallation

To uninstall the system:

1. Stop and disable the service:
   ```
   sudo systemctl stop face-recognition
   sudo systemctl disable face-recognition
   ```

2. Run the uninstallation script:
   ```
   sudo bash /opt/pi5-face-recognition/uninstall.sh
   ```

### Support

For support or questions, please contact the developer or refer to the project repository.

---

## License

This software is provided under the MIT License. See the LICENSE file for details.

---

Enjoy your new face recognition security system!
