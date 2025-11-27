"""
Excavator Controller - GPIO interface for PC817 optocoupler control
Simulates button presses on RC remote to control excavator movements
"""

import time
from typing import Optional
from loguru import logger

try:
    from gpiozero import OutputDevice
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    logger.warning("GPIO not available - running in simulation mode")
    GPIO_AVAILABLE = False


class SimulatedOutputDevice:
    """Mock GPIO device for testing without hardware"""
    def __init__(self, pin):
        self.pin = pin
        self._state = False

    def on(self):
        self._state = True
        logger.debug(f"[SIMULATED] GPIO {self.pin} ON")

    def off(self):
        self._state = False
        logger.debug(f"[SIMULATED] GPIO {self.pin} OFF")

    def close(self):
        pass


class ExcavatorController:
    """
    Controls RC excavator via PC817 optocouplers

    Each optocoupler channel simulates a button press on the RC remote.
    Uses timing-based control since RC excavators lack position feedback.
    """

    def __init__(self, config: dict, simulate: bool = False):
        """
        Initialize excavator controller

        Args:
            config: Configuration dictionary with GPIO pin mappings
            simulate: If True, use simulated GPIO (for testing)
        """
        self.config = config
        self.simulate = simulate or not GPIO_AVAILABLE

        Device = SimulatedOutputDevice if self.simulate else OutputDevice

        # Initialize all GPIO pins for optocoupler control
        gpio_pins = config['gpio']

        self.boom_up = Device(gpio_pins['boom_up'])
        self.boom_down = Device(gpio_pins['boom_down'])
        self.arm_up = Device(gpio_pins['arm_up'])
        self.arm_down = Device(gpio_pins['arm_down'])
        self.bucket_in = Device(gpio_pins['bucket_in'])
        self.bucket_out = Device(gpio_pins['bucket_out'])
        self.turret_left = Device(gpio_pins['turret_left'])
        self.turret_right = Device(gpio_pins['turret_right'])
        self.move_forward = Device(gpio_pins['move_forward'])
        self.move_backward = Device(gpio_pins['move_backward'])
        self.turn_left = Device(gpio_pins['turn_left'])
        self.turn_right = Device(gpio_pins['turn_right'])
        self.special_1 = Device(gpio_pins['special_1'])
        self.special_2 = Device(gpio_pins['special_2'])

        # Timing parameters
        self.timing = config['timing']

        # Track active state
        self.is_moving = False
        self.current_action = None

        logger.info(f"Excavator controller initialized ({'simulated' if self.simulate else 'hardware'} mode)")

    def press_button(self, button: OutputDevice, duration: Optional[float] = None) -> None:
        """
        Simulate a button press by activating optocoupler

        Args:
            button: GPIO output device to activate
            duration: How long to hold (seconds), uses default if None
        """
        if duration is None:
            duration = self.timing['button_press_duration']

        button.on()  # Close optocoupler circuit
        time.sleep(duration)
        button.off()  # Open circuit

    def stop_all(self) -> None:
        """Emergency stop - release all buttons"""
        logger.warning("STOP ALL - Releasing all controls")

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, (OutputDevice, SimulatedOutputDevice)):
                attr.off()

        self.is_moving = False
        self.current_action = None

    # ===== Movement Commands =====

    def move_forward(self, duration: float) -> None:
        """Move excavator forward"""
        logger.info(f"Moving forward for {duration}s")
        self.current_action = "forward"
        self.is_moving = True
        self.press_button(self.move_forward, duration)
        self.is_moving = False

    def move_backward(self, duration: float) -> None:
        """Move excavator backward"""
        logger.info(f"Moving backward for {duration}s")
        self.current_action = "backward"
        self.is_moving = True
        self.press_button(self.move_backward, duration)
        self.is_moving = False

    def turn_left(self, duration: float) -> None:
        """Turn excavator left"""
        logger.info(f"Turning left for {duration}s")
        self.current_action = "turn_left"
        self.press_button(self.turn_left, duration)

    def turn_right(self, duration: float) -> None:
        """Turn excavator right"""
        logger.info(f"Turning right for {duration}s")
        self.current_action = "turn_right"
        self.press_button(self.turn_right, duration)

    # ===== Arm Commands =====

    def boom_raise(self, duration: Optional[float] = None) -> None:
        """Raise boom"""
        dur = duration or self.timing['boom_up_full']
        logger.info(f"Raising boom for {dur}s")
        self.current_action = "boom_up"
        self.press_button(self.boom_up, dur)

    def boom_lower(self, duration: Optional[float] = None) -> None:
        """Lower boom"""
        dur = duration or self.timing['boom_down_full']
        logger.info(f"Lowering boom for {dur}s")
        self.current_action = "boom_down"
        self.press_button(self.boom_down, dur)

    def arm_raise(self, duration: Optional[float] = None) -> None:
        """Raise arm"""
        dur = duration or self.timing['arm_up_full']
        logger.info(f"Raising arm for {dur}s")
        self.current_action = "arm_up"
        self.press_button(self.arm_up, dur)

    def arm_lower(self, duration: Optional[float] = None) -> None:
        """Lower arm"""
        dur = duration or self.timing['arm_down_full']
        logger.info(f"Lowering arm for {dur}s")
        self.current_action = "arm_down"
        self.press_button(self.arm_down, dur)

    def bucket_scoop(self, duration: Optional[float] = None) -> None:
        """Curl bucket inward (scoop motion)"""
        dur = duration or self.timing['bucket_scoop']
        logger.info(f"Scooping bucket for {dur}s")
        self.current_action = "bucket_scoop"
        self.press_button(self.bucket_in, dur)

    def bucket_dump(self, duration: Optional[float] = None) -> None:
        """Tilt bucket outward (dump motion)"""
        dur = duration or self.timing['button_press_duration']
        logger.info(f"Dumping bucket for {dur}s")
        self.current_action = "bucket_dump"
        self.press_button(self.bucket_out, dur)

    def turret_rotate_left(self, duration: float) -> None:
        """Rotate turret counterclockwise"""
        logger.info(f"Rotating turret left for {duration}s")
        self.current_action = "turret_left"
        self.press_button(self.turret_left, duration)

    def turret_rotate_right(self, duration: float) -> None:
        """Rotate turret clockwise"""
        logger.info(f"Rotating turret right for {duration}s")
        self.current_action = "turret_right"
        self.press_button(self.turret_right, duration)

    # ===== Complex Motion Sequences =====

    def home_position(self) -> None:
        """Move to home/transport position"""
        logger.info("Moving to home position")

        # Retract bucket
        self.bucket_scoop(self.timing['bucket_scoop'])
        time.sleep(0.2)

        # Raise arm
        self.arm_raise()
        time.sleep(0.2)

        # Raise boom
        self.boom_raise()

        logger.info("Home position reached")

    def ground_position(self) -> None:
        """Move arm to ground level for scooping"""
        logger.info("Moving to ground position")

        # Lower boom
        self.boom_lower()
        time.sleep(0.2)

        # Extend arm
        self.arm_lower()
        time.sleep(0.2)

        # Position bucket
        self.bucket_dump(0.5)  # Slightly open

        logger.info("Ground position reached")

    def pickup_sequence(self) -> None:
        """Execute complete pickup motion"""
        logger.info("Executing pickup sequence")

        # 1. Lower to ground
        self.ground_position()
        time.sleep(0.3)

        # 2. Scoop
        self.bucket_scoop()
        time.sleep(0.2)

        # 3. Lift
        self.boom_raise(1.0)
        time.sleep(0.2)
        self.arm_raise(0.5)

        logger.info("Pickup sequence complete")

    def dump_sequence(self) -> None:
        """Execute dump motion at disposal location"""
        logger.info("Executing dump sequence")

        # 1. Position at disposal height
        self.boom_raise(0.5)
        time.sleep(0.2)

        # 2. Dump bucket
        self.bucket_dump(1.5)
        time.sleep(0.5)

        # 3. Return to transport
        self.bucket_scoop(0.5)

        logger.info("Dump sequence complete")

    def calibrate_home_position(self, audio_monitor=None, max_duration: float = 10.0) -> bool:
        """
        Calibrate home position by moving to physical limits until motors stall

        This establishes a known starting position for the excavator:
        - Boom fully up (until motor stalls)
        - Arm fully retracted (until motor stalls)
        - Bucket fully closed (until motor stalls)

        Args:
            audio_monitor: AudioMonitor instance for stall detection (optional)
            max_duration: Maximum time to hold each motor (safety timeout)

        Returns:
            True if calibration successful
        """
        logger.info("=" * 60)
        logger.info("CALIBRATING HOME POSITION - Moving to physical limits")
        logger.info("=" * 60)

        # Safety check
        if audio_monitor is None:
            logger.warning("No audio monitor - using time-based calibration (less accurate)")
            use_stall_detection = False
        else:
            use_stall_detection = True

        success = True

        # 1. BOOM UP - Raise until stall or timeout
        logger.info("Step 1/3: Raising boom to maximum height...")
        if use_stall_detection:
            # Hold boom up button and monitor for stall
            start_time = time.time()
            self.boom_up.on()

            while time.time() - start_time < max_duration:
                if audio_monitor.check_for_stall("boom_motor"):
                    logger.info("✓ Boom reached maximum height (stall detected)")
                    self.boom_up.off()
                    audio_monitor.reset_stall_flag()
                    break
                time.sleep(0.1)
            else:
                # Timeout reached
                self.boom_up.off()
                logger.warning("⚠ Boom timeout - may not be at max height")
                success = False
        else:
            # Time-based fallback
            self.press_button(self.boom_up, max_duration)
            logger.info("✓ Boom raised (time-based)")

        time.sleep(0.5)

        # 2. ARM IN - Retract until stall or timeout
        logger.info("Step 2/3: Retracting arm to fully retracted position...")
        if use_stall_detection:
            start_time = time.time()
            self.arm_up.on()

            while time.time() - start_time < max_duration:
                if audio_monitor.check_for_stall("arm_motor"):
                    logger.info("✓ Arm fully retracted (stall detected)")
                    self.arm_up.off()
                    audio_monitor.reset_stall_flag()
                    break
                time.sleep(0.1)
            else:
                self.arm_up.off()
                logger.warning("⚠ Arm timeout - may not be fully retracted")
                success = False
        else:
            self.press_button(self.arm_up, max_duration)
            logger.info("✓ Arm retracted (time-based)")

        time.sleep(0.5)

        # 3. BUCKET OUT - Open bucket until stall or timeout
        logger.info("Step 3/3: Opening bucket to fully extended position...")
        if use_stall_detection:
            start_time = time.time()
            self.bucket_out.on()

            while time.time() - start_time < max_duration:
                if audio_monitor.check_for_stall("bucket_motor"):
                    logger.info("✓ Bucket fully extended (stall detected)")
                    self.bucket_out.off()
                    audio_monitor.reset_stall_flag()
                    break
                time.sleep(0.1)
            else:
                self.bucket_out.off()
                logger.warning("⚠ Bucket timeout - may not be fully extended")
                success = False
        else:
            self.press_button(self.bucket_out, max_duration)
            logger.info("✓ Bucket extended (time-based)")

        time.sleep(0.5)

        # Confirmation
        if success:
            logger.info("=" * 60)
            logger.info("✓ HOME POSITION CALIBRATED SUCCESSFULLY")
            logger.info("  Excavator is now at known starting position:")
            logger.info("  - Boom: Fully raised")
            logger.info("  - Arm: Fully retracted")
            logger.info("  - Bucket: Fully extended")
            logger.info("=" * 60)
        else:
            logger.warning("=" * 60)
            logger.warning("⚠ HOME POSITION CALIBRATION INCOMPLETE")
            logger.warning("  Some motors may not have reached limits")
            logger.warning("  Consider adjusting max_duration or check for obstructions")
            logger.warning("=" * 60)

        return success

    def set_timing(self, param_name: str, value: float) -> None:
        """
        Adjust timing parameter at runtime

        Used by adaptive learning to optimize pickup performance

        Args:
            param_name: Name of timing parameter (e.g., 'arm_down', 'bucket_scoop')
            value: New timing value in seconds
        """
        if param_name in self.timing:
            old_value = self.timing[param_name]
            self.timing[param_name] = value
            logger.info(f"Timing adjusted: {param_name} = {value:.2f}s (was {old_value:.2f}s)")
        else:
            logger.warning(f"Unknown timing parameter: {param_name}")

    def execute_retry_strategy(self, strategy, audio_monitor=None) -> None:
        """
        Execute stall retry strategy

        Args:
            strategy: StallRetryStrategy enum value
            audio_monitor: AudioMonitor instance (for importing enum)
        """
        from hardware.audio_monitor import StallRetryStrategy

        logger.info(f"Executing retry strategy: {strategy.value}")

        if strategy == StallRetryStrategy.BACK_UP:
            # Reverse 0.5m and try again
            logger.info("Strategy: Backing up 0.5m")
            self.move_backward(0.5)
            time.sleep(0.5)

        elif strategy == StallRetryStrategy.ADJUST_ANGLE:
            # Turn 15° and approach from different angle
            logger.info("Strategy: Adjusting approach angle")
            self.turn_left(0.3)  # ~15 degrees
            time.sleep(0.3)
            self.move_forward(0.3)
            time.sleep(0.3)

        elif strategy == StallRetryStrategy.REDUCE_DEPTH:
            # Use shallower scoop (reduce arm_down timing)
            logger.info("Strategy: Reducing scoop depth")
            current_depth = self.timing.get('arm_down', 1.0)
            self.set_timing('arm_down', current_depth * 0.7)  # 30% shallower

        elif strategy == StallRetryStrategy.INCREASE_FORCE:
            # Hold button longer for more force
            logger.info("Strategy: Increasing force (longer button press)")
            current_scoop = self.timing.get('bucket_scoop', 1.0)
            self.set_timing('bucket_scoop', current_scoop * 1.3)  # 30% longer

        elif strategy == StallRetryStrategy.SKIP:
            # Give up on this target
            logger.info("Strategy: Skipping target")
            # No action needed - caller will continue patrol
            pass

    def cleanup(self) -> None:
        """Clean shutdown - release all GPIO"""
        logger.info("Cleaning up excavator controller")
        self.stop_all()

        # Close all GPIO devices
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, (OutputDevice, SimulatedOutputDevice)):
                attr.close()


if __name__ == "__main__":
    """Test excavator controller"""
    from loguru import logger
    import yaml

    # Load config
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Test in simulation mode
    excavator = ExcavatorController(config, simulate=True)

    logger.info("Testing excavator movements...")

    # Test individual commands
    excavator.move_forward(1.0)
    time.sleep(0.5)

    excavator.boom_raise()
    time.sleep(0.5)

    # Test sequence
    excavator.pickup_sequence()
    time.sleep(1.0)

    excavator.dump_sequence()

    excavator.cleanup()
    logger.info("Test complete")
