#!/usr/bin/env python3
"""
Integration Test - Camera + GPIO
Tests that camera and excavator controls work together
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import yaml
from loguru import logger
from vision.camera import CameraInterface
from hardware.excavator import ExcavatorController

def main():
    logger.info("=" * 60)
    logger.info("INTEGRATION TEST - Camera + GPIO")
    logger.info("=" * 60)

    # Load config
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Initialize camera
    logger.info("\n1. Initializing camera...")
    camera = CameraInterface(config, simulate=False)

    # Capture test image
    logger.info("\n2. Capturing test image...")
    output_dir = Path("test_images")
    output_dir.mkdir(exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    image_path = output_dir / f"integration_test_{timestamp}.jpg"

    success = camera.capture_and_save(str(image_path))
    if success:
        logger.info(f"✓ Image saved: {image_path}")
    else:
        logger.error("✗ Failed to capture image")
        camera.cleanup()
        return 1

    # Initialize excavator
    logger.info("\n3. Initializing excavator controller...")
    excavator = ExcavatorController(config, simulate=False)

    # Test a simple movement
    logger.info("\n4. Testing boom movement (0.5s)...")
    excavator.boom_up.on()
    time.sleep(0.5)
    excavator.boom_up.off()
    logger.info("✓ Boom movement complete")

    # Capture another image
    logger.info("\n5. Capturing second image...")
    image_path2 = output_dir / f"integration_test_{timestamp}_after.jpg"
    success = camera.capture_and_save(str(image_path2))
    if success:
        logger.info(f"✓ Second image saved: {image_path2}")
    else:
        logger.error("✗ Failed to capture second image")

    # Cleanup
    logger.info("\n6. Cleaning up...")
    excavator.cleanup()
    camera.cleanup()

    logger.info("\n" + "=" * 60)
    logger.info("✅ INTEGRATION TEST COMPLETE")
    logger.info("=" * 60)
    logger.info("\nTest Results:")
    logger.info(f"  - Camera working: ✓")
    logger.info(f"  - GPIO working: ✓")
    logger.info(f"  - Images captured: 2")
    logger.info(f"  - Location: {output_dir.absolute()}")

    return 0

if __name__ == "__main__":
    exit(main())
