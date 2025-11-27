"""
Test Script - Verify all components
Run this to check your setup
"""

import yaml
from loguru import logger
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported"""
    logger.info("Testing imports...")

    try:
        import numpy
        logger.info("✓ numpy")
    except ImportError:
        logger.error("✗ numpy - Install with: pip install numpy")

    try:
        import cv2
        logger.info("✓ opencv-python")
    except ImportError:
        logger.error("✗ opencv-python - Install with: pip install opencv-python")

    try:
        import picamera2
        logger.info("✓ picamera2")
    except ImportError:
        logger.warning("✗ picamera2 - Install with: sudo apt install python3-picamera2")

    try:
        import gpiozero
        logger.info("✓ gpiozero")
    except ImportError:
        logger.error("✗ gpiozero - Install with: pip install gpiozero")

    try:
        import sounddevice
        logger.info("✓ sounddevice")
    except ImportError:
        logger.error("✗ sounddevice - Install with: pip install sounddevice")

    try:
        import py_trees
        logger.info("✓ py-trees")
    except ImportError:
        logger.error("✗ py-trees - Install with: pip install py-trees")

    try:
        import transitions
        logger.info("✓ transitions")
    except ImportError:
        logger.error("✗ transitions - Install with: pip install transitions")

    try:
        from ultralytics import YOLO
        logger.info("✓ ultralytics")
    except ImportError:
        logger.warning("✗ ultralytics - Install with: pip install ultralytics (needed for training only)")


def test_configuration():
    """Test configuration file"""
    logger.info("\nTesting configuration...")

    config_path = Path("config.yaml")

    if not config_path.exists():
        logger.error("✗ config.yaml not found")
        return False

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        logger.info("✓ config.yaml loaded")

        # Check required sections
        required_sections = ['gpio', 'timing', 'camera', 'vision', 'audio', 'safety']
        for section in required_sections:
            if section in config:
                logger.info(f"  ✓ {section} section present")
            else:
                logger.error(f"  ✗ {section} section missing")

        return True

    except Exception as e:
        logger.error(f"✗ Error loading config: {e}")
        return False


def test_hardware_modules():
    """Test hardware modules in simulation mode"""
    logger.info("\nTesting hardware modules (simulation mode)...")

    try:
        from hardware.excavator import ExcavatorController
        from hardware.audio_monitor import AudioMonitor

        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)

        # Test excavator
        excavator = ExcavatorController(config, simulate=True)
        excavator.move_forward(0.1)
        excavator.cleanup()
        logger.info("✓ ExcavatorController")

        # Test audio monitor
        audio = AudioMonitor(config, simulate=True)
        freq = audio._get_dominant_frequency()
        logger.info(f"✓ AudioMonitor (simulated freq: {freq:.1f} Hz)")

    except Exception as e:
        logger.error(f"✗ Hardware modules failed: {e}")


def test_vision_modules():
    """Test vision modules in simulation mode"""
    logger.info("\nTesting vision modules (simulation mode)...")

    try:
        from vision.camera import CameraInterface
        from vision.detector import PoopDetector
        from vision.marker_detection import RedFlagDetector
        import numpy as np

        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)

        # Test camera
        camera = CameraInterface(config, simulate=True)
        frame = camera.capture_frame()
        if frame is not None:
            logger.info(f"✓ CameraInterface (frame shape: {frame.shape})")
        camera.cleanup()

        # Test detector
        detector = PoopDetector(config, simulate=True)
        test_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        detections = detector.detect(test_img)
        logger.info(f"✓ PoopDetector ({len(detections)} simulated detections)")

        # Test flag detector
        flag_detector = RedFlagDetector(config, simulate=True)
        flag_pos = flag_detector.detect_flag(test_img)
        logger.info(f"✓ RedFlagDetector (flag at: {flag_pos})")

    except Exception as e:
        logger.error(f"✗ Vision modules failed: {e}")


def test_control_modules():
    """Test control modules"""
    logger.info("\nTesting control modules...")

    try:
        from control.state_machines import NavigationStateMachine, ManipulationStateMachine

        # Test navigation state machine
        nav = NavigationStateMachine()
        nav.start_search()
        logger.info(f"✓ NavigationStateMachine (state: {nav.state})")

        # Test manipulation state machine
        arm = ManipulationStateMachine()
        arm.start_pickup()
        logger.info(f"✓ ManipulationStateMachine (state: {arm.state})")

    except Exception as e:
        logger.error(f"✗ Control modules failed: {e}")


def test_safety_modules():
    """Test safety modules"""
    logger.info("\nTesting safety modules...")

    try:
        from safety.watchdog import SafetySystem

        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)

        safety = SafetySystem(config)
        safety.heartbeat()
        status = safety.get_status()
        logger.info(f"✓ SafetySystem (is_safe: {status['is_safe']})")
        safety.cleanup()

    except Exception as e:
        logger.error(f"✗ Safety modules failed: {e}")


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("POOPER SCOOPER - System Test")
    logger.info("=" * 60)

    test_imports()
    test_configuration()
    test_hardware_modules()
    test_vision_modules()
    test_control_modules()
    test_safety_modules()

    logger.info("\n" + "=" * 60)
    logger.info("Test complete!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Fix any errors shown above")
    logger.info("2. Connect hardware (camera, optocouplers, microphone)")
    logger.info("3. Test with: python main.py --simulate")
    logger.info("4. Calibrate audio: python main.py --calibrate-audio")
    logger.info("5. Run autonomous mode: python main.py")


if __name__ == "__main__":
    main()
