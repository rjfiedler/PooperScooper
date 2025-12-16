#!/usr/bin/env python3
"""
Camera Test Script for PooperScooper
Tests the Arducam 8MP camera functionality
"""

import time
import argparse
from pathlib import Path
from picamera2 import Picamera2
from loguru import logger
import yaml

def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_camera_basic():
    """Basic camera initialization test"""
    logger.info("=" * 60)
    logger.info("CAMERA TEST - Basic Initialization")
    logger.info("=" * 60)

    try:
        logger.info("Initializing camera...")
        camera = Picamera2()

        logger.info("Camera detected successfully!")
        logger.info(f"Camera model: {camera.camera_properties.get('Model', 'Unknown')}")

        # Get camera configuration
        camera_config = camera.create_still_configuration()
        logger.info(f"Camera configuration: {camera_config}")

        camera.close()
        logger.info("✓ Camera basic test PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ Camera basic test FAILED: {e}")
        return False

def test_camera_capture(output_dir="test_images"):
    """Test camera capture functionality"""
    logger.info("=" * 60)
    logger.info("CAMERA TEST - Image Capture")
    logger.info("=" * 60)

    try:
        # Load config
        config = load_config()
        cam_config = config['camera']

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        logger.info(f"Resolution: {cam_config['resolution']}")
        logger.info(f"Rotation: {cam_config['rotation']}°")

        # Initialize camera
        logger.info("Initializing camera...")
        camera = Picamera2()

        # Configure camera
        config_dict = camera.create_still_configuration(
            main={"size": tuple(cam_config['resolution'])},
            transform={"rotation": cam_config['rotation']}
        )
        camera.configure(config_dict)

        # Start camera
        logger.info("Starting camera...")
        camera.start()

        # Allow camera to warm up
        logger.info("Warming up camera (2 seconds)...")
        time.sleep(2)

        # Capture test image
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        image_path = output_path / f"test_capture_{timestamp}.jpg"

        logger.info(f"Capturing image to: {image_path}")
        camera.capture_file(str(image_path))

        # Verify file was created
        if image_path.exists():
            file_size = image_path.stat().st_size / 1024  # KB
            logger.info(f"✓ Image captured successfully!")
            logger.info(f"  File: {image_path}")
            logger.info(f"  Size: {file_size:.1f} KB")
        else:
            logger.error("✗ Image file was not created")
            return False

        # Stop camera
        camera.stop()
        camera.close()

        logger.info("=" * 60)
        logger.info("✓ Camera capture test PASSED")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"✗ Camera capture test FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_camera_preview(duration=5):
    """Test camera preview (headless - just runs camera for duration)"""
    logger.info("=" * 60)
    logger.info(f"CAMERA TEST - Preview ({duration}s)")
    logger.info("=" * 60)

    try:
        config = load_config()
        cam_config = config['camera']

        logger.info("Initializing camera for preview...")
        camera = Picamera2()

        # Use preview configuration
        preview_config = camera.create_preview_configuration(
            main={"size": tuple(cam_config['resolution'])},
            transform={"rotation": cam_config['rotation']}
        )
        camera.configure(preview_config)

        logger.info("Starting preview...")
        camera.start()

        logger.info(f"Camera running for {duration} seconds...")
        for i in range(duration):
            logger.info(f"  {i+1}/{duration} seconds...")
            time.sleep(1)

        camera.stop()
        camera.close()

        logger.info("✓ Camera preview test PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ Camera preview test FAILED: {e}")
        return False

def test_camera_multiple_captures(count=3):
    """Test capturing multiple images"""
    logger.info("=" * 60)
    logger.info(f"CAMERA TEST - Multiple Captures ({count} images)")
    logger.info("=" * 60)

    try:
        config = load_config()
        cam_config = config['camera']

        output_path = Path("test_images")
        output_path.mkdir(exist_ok=True)

        logger.info("Initializing camera...")
        camera = Picamera2()

        config_dict = camera.create_still_configuration(
            main={"size": tuple(cam_config['resolution'])},
            transform={"rotation": cam_config['rotation']}
        )
        camera.configure(config_dict)
        camera.start()

        logger.info("Warming up...")
        time.sleep(2)

        for i in range(count):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            image_path = output_path / f"test_multi_{i+1}_{timestamp}.jpg"

            logger.info(f"[{i+1}/{count}] Capturing: {image_path.name}")
            camera.capture_file(str(image_path))

            if image_path.exists():
                file_size = image_path.stat().st_size / 1024
                logger.info(f"  ✓ Captured ({file_size:.1f} KB)")
            else:
                logger.error(f"  ✗ Failed to capture image {i+1}")
                return False

            time.sleep(0.5)

        camera.stop()
        camera.close()

        logger.info("=" * 60)
        logger.info("✓ Multiple capture test PASSED")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"✗ Multiple capture test FAILED: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test camera functionality")
    parser.add_argument('--test', choices=['basic', 'capture', 'preview', 'multi', 'all'],
                       default='all', help='Test to run')
    parser.add_argument('--output', default='test_images', help='Output directory for test images')
    parser.add_argument('--preview-duration', type=int, default=5,
                       help='Preview duration in seconds')
    parser.add_argument('--multi-count', type=int, default=3,
                       help='Number of images for multi-capture test')

    args = parser.parse_args()

    results = {}

    if args.test == 'basic' or args.test == 'all':
        results['basic'] = test_camera_basic()
        print()

    if args.test == 'capture' or args.test == 'all':
        results['capture'] = test_camera_capture(args.output)
        print()

    if args.test == 'preview' or args.test == 'all':
        results['preview'] = test_camera_preview(args.preview_duration)
        print()

    if args.test == 'multi' or args.test == 'all':
        results['multi'] = test_camera_multiple_captures(args.multi_count)
        print()

    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name.upper()}: {status}")

    logger.info("=" * 60)

    all_passed = all(results.values())
    if all_passed:
        logger.info("🎉 All camera tests PASSED!")
    else:
        logger.warning("⚠ Some camera tests FAILED - check output above")

    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
