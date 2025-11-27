#!/usr/bin/env python3
"""
GPIO Test Script - Test all excavator controls
Activates each GPIO pin for 1 second to verify PC817 optocoupler connections
"""

import time
import yaml
from pathlib import Path
from loguru import logger

# Import excavator controller
from hardware.excavator import ExcavatorController


def test_all_controls(simulate: bool = False):
    """
    Test all excavator controls by activating each for 1 second

    Args:
        simulate: If True, run in simulation mode (no actual GPIO)
    """
    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Initialize excavator
    logger.info("=" * 60)
    logger.info("EXCAVATOR GPIO TEST - All Controls")
    logger.info("=" * 60)

    excavator = ExcavatorController(config, simulate=simulate)

    test_duration = 1.0  # 1 second per test

    # List of all controls to test
    tests = [
        # (name, gpio_object, description)
        ("BOOM UP", excavator.boom_up, "Raise boom"),
        ("BOOM DOWN", excavator.boom_down, "Lower boom"),
        ("ARM UP", excavator.arm_up, "Retract arm"),
        ("ARM DOWN", excavator.arm_down, "Extend arm"),
        ("BUCKET IN", excavator.bucket_in, "Close/scoop bucket"),
        ("BUCKET OUT", excavator.bucket_out, "Open/dump bucket"),
        ("TURRET LEFT", excavator.turret_left, "Rotate turret left"),
        ("TURRET RIGHT", excavator.turret_right, "Rotate turret right"),
        ("MOVE FORWARD", excavator.move_forward, "Drive forward"),
        ("MOVE BACKWARD", excavator.move_backward, "Drive backward"),
        ("TURN LEFT", excavator.turn_left, "Turn left"),
        ("TURN RIGHT", excavator.turn_right, "Turn right"),
        ("SPECIAL 1", excavator.special_1, "Special function 1"),
        ("SPECIAL 2", excavator.special_2, "Special function 2"),
    ]

    logger.info(f"\nTesting {len(tests)} controls, {test_duration}s each")
    logger.info("Watch excavator for movement on each test\n")

    # Test each control
    for i, (name, gpio_obj, description) in enumerate(tests, 1):
        logger.info(f"[{i}/{len(tests)}] Testing: {name}")
        logger.info(f"    Description: {description}")
        logger.info(f"    GPIO Pin: {gpio_obj.pin if hasattr(gpio_obj, 'pin') else 'N/A'}")
        logger.info(f"    Activating for {test_duration}s...")

        # Activate GPIO
        gpio_obj.on()

        # Wait
        time.sleep(test_duration)

        # Deactivate
        gpio_obj.off()

        logger.info(f"    ✓ Complete\n")

        # Small pause between tests
        time.sleep(0.5)

    # Cleanup
    excavator.cleanup()

    logger.info("=" * 60)
    logger.info("GPIO TEST COMPLETE")
    logger.info("=" * 60)
    logger.info("\nVerify that each control activated correctly:")
    logger.info("  - Boom should have moved up and down")
    logger.info("  - Arm should have moved in and out")
    logger.info("  - Bucket should have closed and opened")
    logger.info("  - Turret should have rotated left and right")
    logger.info("  - Excavator should have driven forward and backward")
    logger.info("  - Excavator should have turned left and right")
    logger.info("\nIf any control did not work, check:")
    logger.info("  1. GPIO pin mapping in config.yaml")
    logger.info("  2. PC817 optocoupler connections")
    logger.info("  3. RC remote button assignments")


def test_quick_sequence(simulate: bool = False):
    """
    Quick test sequence - just arm movements for faster testing

    Args:
        simulate: If True, run in simulation mode
    """
    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    logger.info("=" * 60)
    logger.info("QUICK ARM TEST - Boom, Arm, Bucket only")
    logger.info("=" * 60)

    excavator = ExcavatorController(config, simulate=simulate)

    # Quick arm sequence
    logger.info("\n1. Testing BOOM UP (1s)")
    excavator.boom_up.on()
    time.sleep(1.0)
    excavator.boom_up.off()
    time.sleep(0.5)

    logger.info("2. Testing BOOM DOWN (1s)")
    excavator.boom_down.on()
    time.sleep(1.0)
    excavator.boom_down.off()
    time.sleep(0.5)

    logger.info("3. Testing ARM UP (1s)")
    excavator.arm_up.on()
    time.sleep(1.0)
    excavator.arm_up.off()
    time.sleep(0.5)

    logger.info("4. Testing ARM DOWN (1s)")
    excavator.arm_down.on()
    time.sleep(1.0)
    excavator.arm_down.off()
    time.sleep(0.5)

    logger.info("5. Testing BUCKET IN (1s)")
    excavator.bucket_in.on()
    time.sleep(1.0)
    excavator.bucket_in.off()
    time.sleep(0.5)

    logger.info("6. Testing BUCKET OUT (1s)")
    excavator.bucket_out.on()
    time.sleep(1.0)
    excavator.bucket_out.off()

    excavator.cleanup()
    logger.info("\n✓ Quick arm test complete")


def test_single_control(control_name: str, duration: float = 1.0, simulate: bool = False):
    """
    Test a single control by name

    Args:
        control_name: Name of control (e.g., 'boom_up', 'arm_down')
        duration: How long to activate (seconds)
        simulate: If True, run in simulation mode
    """
    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    excavator = ExcavatorController(config, simulate=simulate)

    # Get the GPIO object by name
    if not hasattr(excavator, control_name):
        logger.error(f"Unknown control: {control_name}")
        logger.info("Valid controls: boom_up, boom_down, arm_up, arm_down, bucket_in, bucket_out,")
        logger.info("               turret_left, turret_right, move_forward, move_backward,")
        logger.info("               turn_left, turn_right, special_1, special_2")
        return

    gpio_obj = getattr(excavator, control_name)

    logger.info(f"Testing {control_name} for {duration}s...")
    gpio_obj.on()
    time.sleep(duration)
    gpio_obj.off()
    logger.info(f"✓ {control_name} test complete")

    excavator.cleanup()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test excavator GPIO controls")
    parser.add_argument('--simulate', action='store_true', help='Run in simulation mode (no hardware)')
    parser.add_argument('--quick', action='store_true', help='Run quick arm test only')
    parser.add_argument('--control', type=str, help='Test single control (e.g., boom_up)')
    parser.add_argument('--duration', type=float, default=1.0, help='Duration in seconds (default: 1.0)')

    args = parser.parse_args()

    if args.control:
        # Test single control
        test_single_control(args.control, args.duration, args.simulate)
    elif args.quick:
        # Quick arm test
        test_quick_sequence(args.simulate)
    else:
        # Full test
        test_all_controls(args.simulate)
