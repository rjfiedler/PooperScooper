# Quick Start Guide

Get your Pooper Scooper up and running in 30 minutes!

## Step 1: Hardware Setup (10 minutes)

### Connect the Camera
1. Power off Raspberry Pi
2. Connect Arducam 8MP to CSI port
3. Power on and enable camera:
```bash
sudo raspi-config
# Navigate to: Interface Options > Camera > Enable
```

### Connect PC817 Optocouplers
1. Wire PC817 inputs to Raspberry Pi GPIO pins (with 220Ω resistors)
2. Connect PC817 outputs across RC remote button contacts
3. Verify pin mappings match [config.yaml](config.yaml):
   - GPIO 17 → Boom Up
   - GPIO 18 → Boom Down
   - GPIO 27 → Arm Up
   - (etc... see config.yaml for all 14 channels)

### Connect USB Microphone
1. Plug into any USB port
2. Test: `arecord -l` (should list your microphone)

## Step 2: Software Installation (10 minutes)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-opencv python3-numpy
sudo apt install -y libatlas-base-dev libportaudio2
sudo apt install -y python3-picamera2

# Clone/copy project
cd ~/pooperscooper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

## Step 3: Test the System (5 minutes)

```bash
# Run system test
python scripts/test_system.py
```

Fix any errors before proceeding!

## Step 4: Initial Testing (5 minutes)

### Test in Simulation Mode
```bash
python main.py --simulate
```

This runs without hardware - verify no errors occur.

### Test Camera
```bash
python -c "from vision.camera import CameraInterface; import yaml; \
  config = yaml.safe_load(open('config.yaml')); \
  cam = CameraInterface(config); \
  cam.capture_and_save('test.jpg'); \
  cam.cleanup()"
```

Check that `test.jpg` was created.

### Test Excavator Control
```bash
python -c "from hardware.excavator import ExcavatorController; import yaml; \
  config = yaml.safe_load(open('config.yaml')); \
  exc = ExcavatorController(config, simulate=False); \
  exc.boom_raise(0.5); \
  exc.cleanup()"
```

**Verify boom moves!** If not, check GPIO wiring.

## Step 5: Calibration (Optional - 5 minutes)

### Audio Calibration
```bash
python main.py --calibrate-audio
```

Follow prompts to record baseline motor sounds.

## Step 6: Prepare for Autonomous Operation

### 1. Get a Trained Model

**Option A: Download Pre-trained Model** (recommended)
- Download from ScatSpotter dataset or use your own
- Place in `models/poop_detector.tflite`

**Option B: Train Your Own**
```bash
# Collect training images in your yard
python -c "from vision.camera import CameraInterface; import yaml; \
  config = yaml.safe_load(open('config.yaml')); \
  cam = CameraInterface(config); \
  import os; os.makedirs('training_data', exist_ok=True); \
  [cam.capture_and_save(f'training_data/img_{i:04d}.jpg') for i in range(100)]; \
  cam.cleanup()"

# Annotate images using Roboflow or LabelImg
# Then train:
python scripts/train_model.py --data training_data/data.yaml --epochs 100

# Convert to TFLite:
python scripts/convert_to_tflite.py \
  --model runs/detect/poop_detector/weights/best.pt \
  --output models/poop_detector.tflite
```

### 2. Place Red Flag
- Put a red flag/marker at your disposal location
- Make it clearly visible from excavator's camera height

## Step 7: Run Autonomous Mode!

```bash
# Start the system
python main.py
```

### What to Expect:
1. System initializes (5-10 seconds)
2. Excavator moves to home position
3. Camera scans for poop
4. When detected, excavator approaches
5. Executes pickup sequence
6. Navigates to red flag
7. Dumps load
8. Repeats!

### Monitoring:
- Watch terminal for logs
- Check `logs/pooperscooper.log` for detailed history
- Emergency stop: Press Ctrl+C or use RC remote

## Troubleshooting

### "Camera not found"
```bash
libcamera-hello  # Test camera
sudo raspi-config  # Enable camera interface
```

### "GPIO permission denied"
```bash
sudo usermod -a -G gpio $USER
# Log out and back in
```

### "No poop detected"
- Verify model is loaded: `ls -lh models/poop_detector.tflite`
- Check confidence threshold in config.yaml (try lowering to 0.5)
- Test with known poop sample

### "Excavator not moving"
- Check GPIO pin numbers (BCM vs BOARD)
- Verify optocoupler wiring with multimeter
- Test individual commands in Python

### "Low FPS"
- Normal on Pi without GPU: 2-5 FPS is expected
- Reduce resolution in config.yaml
- Use INT8 quantized model
- Consider Coral Edge TPU for 10-20x speedup

## Performance Tuning

### Adjust config.yaml:

**For Better Accuracy:**
```yaml
vision:
  confidence_threshold: 0.8  # Higher = fewer false positives
  multi_frame_verification: 5  # More frames = more reliable
```

**For Better Speed:**
```yaml
camera:
  resolution: [1280, 720]  # Lower resolution
vision:
  inference_resolution: [320, 320]  # Smaller input
```

**For Different Excavator:**
```yaml
timing:
  boom_up_full: 3.0  # Adjust based on your excavator speed
  arm_down_full: 2.5
  # Test and tune these values
```

## Safety Reminders

- ⚠️ Keep RC remote in hand for manual override
- ⚠️ Test in enclosed area first
- ⚠️ No people or pets in operating area
- ⚠️ Emergency stop works: Ctrl+C or RC remote
- ⚠️ Supervise during initial runs

## Next Steps

Once basic operation works:

1. **Collect Training Data**: Capture images in various lighting
2. **Fine-tune Model**: Train on your specific yard/grass type
3. **Optimize Paths**: Adjust navigation behavior in `control/behavior_tree.py`
4. **Add Features**:
   - Battery monitoring
   - Scheduled operation
   - Mobile app control
   - Multiple disposal locations

## Getting Help

- Check logs: `tail -f logs/pooperscooper.log`
- Run tests: `python scripts/test_system.py`
- Increase log verbosity: Set `logging.level: DEBUG` in config.yaml

---

**Happy Scooping! 💩🚜**
