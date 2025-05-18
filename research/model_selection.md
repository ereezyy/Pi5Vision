# Face Recognition Model Selection and Implementation

## Selected Model: RetinaFace MobileNet V1

After researching compatible models for the Raspberry Pi 5 with Hailo AI HAT+ (26 TOPS), I've selected the RetinaFace MobileNet V1 model for the following reasons:

1. **Hailo Compatibility**: The model is officially available in the Hailo Model Zoo and has been compiled for the Hailo-8 architecture
2. **Community Validation**: Successfully tested and documented by community members on the exact hardware configuration (Pi5 + Hailo HAT)
3. **Performance**: Optimized for edge devices with real-time processing capabilities
4. **Accuracy**: Provides high-quality face detection with bounding boxes and confidence scores
5. **Integration**: Can be used with GStreamer pipelines for camera integration

## Implementation Requirements

### Software Dependencies
- HailoRT version 4.18.0 (required for latest model compatibility)
- GStreamer with Hailo plugins
- TAPPAS (Hailo's Tools, APIs, and Platforms for AI Solutions) version 3.29.0+
- Python 3.11 with Hailo bindings

### Model Setup
1. Download the RetinaFace MobileNet V1 model (.HEF file) from the Hailo Model Zoo
2. Use the pre-compiled model as the data flow compiler isn't available on Pi5
3. Integrate with GStreamer pipeline for real-time processing

### Pipeline Architecture
The face recognition system will use a multi-stage pipeline:
1. **Camera Input**: Capture video stream from USB camera
2. **Preprocessing**: Scale and format frames for the neural network
3. **Face Detection**: Use RetinaFace model to detect faces in frames
4. **Face Recognition**: Extract face embeddings and compare with database
5. **Tracking**: Track faces across frames to maintain identity
6. **Alerting**: Generate alerts for new or unrecognized faces

## GStreamer Pipeline for Face Detection

For USB camera input:
```
gst-launch-1.0 hailomuxer name=hmux \
    v4l2src device=/dev/video0 ! \
    video/x-raw,format=NV12,width=1280,height=720,framerate=30/1 ! \
    queue name=hailo_preprocess_q_0 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    videoscale qos=false n-threads=2 ! video/x-raw, pixel-aspect-ratio=1/1 ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    videoconvert n-threads=2 qos=false ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    hailonet hef-path=/path/to/retinaface_mobilenet_v1.hef ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    hailofilter so-path=/usr/lib/aarch64-linux-gnu/post_processes/libface_detection_post.so name=face_detection_hailofilter qos=false function_name=retinaface ! \
    queue leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! \
    hailooverlay name=hailo_overlay qos=false show-confidence=false line-thickness=5 font-thickness=2 ! \
    videoconvert ! \
    autovideosink
```

## Face Recognition Extension

To extend the face detection to full face recognition, we'll need to:
1. Extract face embeddings from detected faces
2. Maintain a database of known faces and their embeddings
3. Compare detected face embeddings with the database
4. Implement a tracking system to maintain identity across frames
5. Create an alert system for new or unrecognized faces

This will be implemented in Python, leveraging the Hailo API and additional face recognition libraries.

## Next Steps

1. Implement the camera integration and real-time processing pipeline
2. Add face embedding extraction and comparison functionality
3. Create a database for storing known faces
4. Implement the tracking and alerting system
5. Package everything for easy installation on Pi5 with Hailo
