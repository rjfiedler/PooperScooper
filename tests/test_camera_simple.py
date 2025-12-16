#!/usr/bin/env python3
"""
Super Simple Camera Test for Arducam 8MP on Raspberry Pi 5
"""

import time
from pathlib import Path
from picamera2 import Picamera2

def main():
    print("=" * 60)
    print("SIMPLE CAMERA TEST - Arducam 8MP on Raspberry Pi 5")
    print("=" * 60)
    print()

    # Check for cameras
    print("Step 1: Checking for available cameras...")
    cameras = Picamera2.global_camera_info()
    print(f"Found {len(cameras)} camera(s)")

    if len(cameras) == 0:
        print("\n❌ ERROR: No cameras detected!")
        print("\nTroubleshooting:")
        print("  1. Is the camera physically connected to the CSI port?")
        print("  2. Is the ribbon cable properly seated (blue side up on Pi 5)?")
        print("  3. Did you enable the camera interface? Run: sudo raspi-config")
        print("     -> Interface Options -> Camera -> Enable")
        print("  4. Have you rebooted after connecting? Run: sudo reboot")
        return 1

    print("\n✓ Camera detected!")
    for i, cam in enumerate(cameras):
        print(f"  Camera {i}: {cam}")
    print()

    # Initialize camera
    print("Step 2: Initializing camera...")
    try:
        picam2 = Picamera2()
        print("✓ Camera initialized")
    except Exception as e:
        print(f"❌ Failed to initialize camera: {e}")
        return 1
    print()

    # Get camera info
    print("Step 3: Camera information...")
    props = picam2.camera_properties
    print(f"  Model: {props.get('Model', 'Unknown')}")
    print(f"  Location: {props.get('Location', 'Unknown')}")
    print()

    # Configure for still capture
    print("Step 4: Configuring camera for 1920x1080 capture...")
    config = picam2.create_still_configuration(
        main={"size": (1920, 1080)}
    )
    picam2.configure(config)
    print("✓ Camera configured")
    print()

    # Start camera
    print("Step 5: Starting camera...")
    picam2.start()
    print("✓ Camera started")
    print()

    # Warm up
    print("Step 6: Warming up camera (2 seconds)...")
    time.sleep(2)
    print("✓ Camera ready")
    print()

    # Capture image
    print("Step 7: Capturing test image...")
    output_dir = Path("test_images")
    output_dir.mkdir(exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    image_path = output_dir / f"camera_test_{timestamp}.jpg"

    print(f"  Saving to: {image_path}")
    picam2.capture_file(str(image_path))

    # Verify
    if image_path.exists():
        file_size_kb = image_path.stat().st_size / 1024
        print(f"✓ Image captured successfully!")
        print(f"  Size: {file_size_kb:.1f} KB")
    else:
        print("❌ Image file was not created")
        picam2.stop()
        picam2.close()
        return 1
    print()

    # Cleanup
    print("Step 8: Stopping camera...")
    picam2.stop()
    picam2.close()
    print("✓ Camera stopped")
    print()

    print("=" * 60)
    print("✅ SUCCESS! Camera test completed")
    print("=" * 60)
    print(f"\nTest image saved to: {image_path.absolute()}")
    print("Open the image to verify the camera is working correctly.")
    return 0

if __name__ == "__main__":
    exit(main())
