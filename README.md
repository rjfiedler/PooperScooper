# Pooper Scooper - Autonomous Dog Waste Cleanup System

An autonomous RC excavator system that uses computer vision to detect, pick up, and dispose of dog waste in your backyard.

## System Overview

This project uses a Raspberry Pi 5 to control an RC excavator with the following capabilities:
- **Computer Vision**: YOLOv8-based poop detection using TensorFlow Lite
- **Autonomous Navigation**: Visual marker-based navigation to disposal location
- **Motor Stall Detection**: Audio-based FFT analysis for detecting mechanical issues
- **Safety Systems**: Multi-layer safety with watchdog timer and emergency stop
- **Behavioral Control**: Behavior tree + state machines for robust decision-making

## Hardware Requirements

### Core Components
- Raspberry Pi 5 (4GB or 8GB recommended)
- Arducam 8MP Camera Module
- PC817 Optocoupler Breakout Board (16 channels)
- USB Microphone (for motor stall detection)
- RC Excavator with remote control
- MicroSD Card (64GB+ recommended)
- Power supply for Raspberry Pi

### Optional Enhancements
- Coral Edge TPU USB Accelerator (10-20x vision speedup)
- MPU6050 IMU (for tilt detection)
- Waterproof enclosure for outdoor operation

## Installation

### 1. Raspberry Pi Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-pip python3-opencv python3-numpy
sudo apt install -y libatlas-base-dev libportaudio2
sudo apt install -y python3-picamera2

# For GPIO access without sudo
sudo usermod -a -G gpio,i2c,spi $USER
```

### 2. Python Environment

```bash
# Clone or copy this project
cd ~/pooperscooper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Hardware Connection

#### PC817 Optocoupler Wiring
1. Connect Raspberry Pi GPIO pins to PC817 input (with 220Ω resistors)
2. Connect PC817 output across RC remote button contacts
3. Refer to [config.yaml](config.yaml) for GPIO pin mappings

Pin assignments (BCM numbering):
- GPIO 17: Boom Up
- GPIO 18: Boom Down
- GPIO 27: Arm Up
- GPIO 22: Arm Down
- (See config.yaml for complete mapping)

#### Camera
- Connect Arducam to Raspberry Pi CSI port
- Enable camera in raspi-config

#### Microphone
- Connect USB microphone to any USB port

## Configuration

Edit [config.yaml](config.yaml) to customize:
- GPIO pin mappings
- Timing parameters for excavator movements
- Vision detection thresholds
- Safety limits
- Audio analysis parameters

## Usage

### First-Time Setup

1. **Test Hardware** (simulation mode):
```bash
python main.py --simulate
```

2. **Calibrate Audio Monitoring**:
```bash
python main.py --calibrate-audio
```
This records baseline frequency signatures for each motor.

3. **Collect Training Data** (if using custom model):
```bash
# Capture images of poop in your yard
python -c "from vision.camera import CameraInterface; import yaml; \
  config = yaml.safe_load(open('config.yaml')); \
  cam = CameraInterface(config); \
  [cam.capture_and_save(f'training_data/img_{i}.jpg') for i in range(100)]"
```

### Running the System

**Full Autonomous Mode**:
```bash
python main.py
```

**Simulation Mode** (no hardware):
```bash
python main.py --simulate
```

**Custom Configuration**:
```bash
python main.py --config my_config.yaml --max-iterations 500
```

### Remote Monitoring

The system includes MQTT-based status updates. You can monitor operation:

```bash
# Subscribe to status updates (requires MQTT broker)
mosquitto_sub -t "pooperscooper/status"
```

## Training the Detection Model

### Option 1: Use Pre-trained ScatSpotter Model

Download the ScatSpotter dataset (42GB):
```bash
# Install girder-client
pip install girder-client

# Download dataset
girder-cli --api-url https://data.kitware.com/api/v1 \
  download <dataset_id> training_data/
```

### Option 2: Train Custom Model

```bash
# 1. Annotate your images using Roboflow or LabelImg

# 2. Train YOLOv8 model
python scripts/train_model.py --data training_data/ --epochs 100

# 3. Convert to TensorFlow Lite
python scripts/convert_to_tflite.py --model runs/detect/train/weights/best.pt \
  --output models/poop_detector.tflite
```

## Project Structure

```
pooperscooper/
├── main.py                  # Main entry point
├── config.yaml              # Configuration
├── requirements.txt         # Python dependencies
├── vision/                  # Computer vision modules
│   ├── camera.py            # Arducam interface
│   ├── detector.py          # TFLite poop detection
│   └── marker_detection.py  # Red flag detection
├── hardware/                # Hardware control
│   ├── excavator.py         # GPIO/optocoupler control
│   └── audio_monitor.py     # Motor stall detection
├── control/                 # Behavior control
│   ├── behavior_tree.py     # Main behavior tree
│   └── state_machines.py    # Navigation/arm FSMs
├── safety/                  # Safety systems
│   └── watchdog.py          # Watchdog timer
├── utils/                   # Utilities
│   └── logging_setup.py     # Logging configuration
├── models/                  # Trained models
│   └── poop_detector.tflite
└── logs/                    # Log files
```

## Safety Features

The system includes multiple safety layers:

1. **Watchdog Timer**: Monitors heartbeat and triggers emergency stop if main loop hangs
2. **Operation Timeout**: Auto-shutdown after 30 minutes (configurable)
3. **Motor Stall Detection**: Audio monitoring detects mechanical issues
4. **Emergency Stop**: Immediate halt of all motors
5. **Manual Override**: RC remote maintains control

### Emergency Stop

To trigger emergency stop:
- Press Ctrl+C in terminal
- Use physical RC remote
- Safety watchdog will trigger automatically if issues detected

## Troubleshooting

### Camera Not Detected
```bash
# Check camera connection
libcamera-hello

# Enable camera interface
sudo raspi-config
# Navigate to Interface Options > Camera
```

### GPIO Permission Errors
```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER
# Log out and back in
```

### Low FPS on Detection
- Use INT8 quantized model (see [detector.py](vision/detector.py))
- Reduce input resolution in config.yaml
- Consider Coral Edge TPU accelerator
- Expected: 2-5 FPS on Pi 5 without TPU

### Optocoupler Not Triggering
- Check resistor values (200-220Ω recommended)
- Verify GPIO pin mappings in config.yaml
- Test with multimeter across optocoupler output

## Performance Metrics

Expected performance on Raspberry Pi 5:
- **Detection Speed**: 2-5 FPS (TFLite INT8)
- **Detection Accuracy**: >85% (with ScatSpotter dataset)
- **Pickup Success Rate**: 60-80% (varies by terrain/excavator)
- **Battery Life**: 30-45 minutes (depends on excavator battery)

## Development

### Running Tests
```bash
# Test individual modules
python -m vision.camera
python -m vision.detector
python -m hardware.excavator --simulate
python -m control.state_machines
```

### Adding New Features

The modular design makes it easy to extend:
- Add new vision detectors in `vision/`
- Implement custom motion sequences in `hardware/excavator.py`
- Extend behavior tree in `control/behavior_tree.py`

## Contributing

This is a personal project, but suggestions and improvements are welcome!

1. Test thoroughly in simulation mode first
2. Add proper error handling
3. Update configuration documentation
4. Follow existing code style

## License

MIT License - See LICENSE file for details

## Acknowledgments

- **ScatSpotter Dataset**: [arXiv:2412.16473](https://arxiv.org/html/2412.16473v1)
- **YOLOv8**: Ultralytics
- **py_trees**: Behavior tree framework
- **Picamera2**: Raspberry Pi camera library

## Safety Disclaimer

This system controls a motorized device. Always:
- Test in a safe, enclosed area
- Keep manual RC remote accessible
- Supervise during initial testing
- Ensure no people or pets in operating area
- Verify emergency stop works before autonomous operation

Use at your own risk. The authors are not liable for any damage or injury.

## Contact

For questions or issues, please open an issue on GitHub.

---

**Status**: Experimental - Under active development

**Last Updated**: 2025-11-23
