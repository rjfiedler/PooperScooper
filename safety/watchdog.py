"""
Safety System - Watchdog timer and multi-layer safety
Monitors system health and triggers emergency stop if needed
"""

import time
import threading
from typing import Optional
from loguru import logger


class SafetySystem:
    """
    Multi-layer safety system for excavator

    Layers:
    1. Watchdog timer (heartbeat monitoring)
    2. Operation timeout
    3. Motor stall detection integration
    4. Emergency stop flag
    """

    def __init__(self, config: dict):
        """
        Initialize safety system

        Args:
            config: Safety configuration dictionary
        """
        self.config = config

        self.watchdog_timeout = config['safety']['watchdog_timeout']
        self.max_operation_time = config['safety']['max_operation_time']
        self.stall_retry_attempts = config['safety']['stall_retry_attempts']

        # State tracking
        self.last_heartbeat = time.time()
        self.start_time = time.time()
        self.emergency_stop = False
        self.stall_count = 0

        # Threading
        self.watchdog_thread: Optional[threading.Thread] = None
        self.running = False

        logger.info(f"Safety system initialized (watchdog timeout: {self.watchdog_timeout}s)")

    def start_watchdog(self) -> None:
        """Start watchdog monitoring thread"""
        if self.running:
            logger.warning("Watchdog already running")
            return

        self.running = True
        self.watchdog_thread = threading.Thread(target=self._watchdog_monitor, daemon=True)
        self.watchdog_thread.start()

        logger.info("Watchdog thread started")

    def stop_watchdog(self) -> None:
        """Stop watchdog monitoring"""
        self.running = False

        if self.watchdog_thread:
            self.watchdog_thread.join(timeout=2.0)

        logger.info("Watchdog thread stopped")

    def _watchdog_monitor(self) -> None:
        """Watchdog monitoring loop (runs in separate thread)"""
        while self.running:
            current_time = time.time()

            # Check heartbeat timeout
            time_since_heartbeat = current_time - self.last_heartbeat

            if time_since_heartbeat > self.watchdog_timeout:
                logger.critical(f"WATCHDOG TIMEOUT: No heartbeat for {time_since_heartbeat:.1f}s")
                self.trigger_emergency_stop("Watchdog timeout")

            # Check maximum operation time
            operation_time = current_time - self.start_time

            if operation_time > self.max_operation_time:
                logger.warning(f"Maximum operation time ({self.max_operation_time}s) reached")
                self.trigger_emergency_stop("Operation timeout")

            # Sleep before next check
            time.sleep(0.5)

    def heartbeat(self) -> None:
        """
        Send heartbeat signal to watchdog

        Call this regularly from main loop (at least every watchdog_timeout seconds)
        """
        self.last_heartbeat = time.time()

    def is_safe(self) -> bool:
        """
        Check if system is in safe state

        Returns:
            True if safe to operate
        """
        if self.emergency_stop:
            return False

        # Check heartbeat freshness
        time_since_heartbeat = time.time() - self.last_heartbeat

        if time_since_heartbeat > self.watchdog_timeout:
            logger.warning(f"Heartbeat stale ({time_since_heartbeat:.1f}s)")
            return False

        return True

    def trigger_emergency_stop(self, reason: str) -> None:
        """
        Trigger emergency stop

        Args:
            reason: Reason for emergency stop
        """
        if not self.emergency_stop:
            logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
            self.emergency_stop = True

            # TODO: Send signal to stop all motors immediately
            # This should call excavator.stop_all()

    def reset_emergency_stop(self) -> None:
        """
        Reset emergency stop flag (manual reset required)

        Use with caution - only after verifying issue is resolved
        """
        logger.warning("Resetting emergency stop flag")
        self.emergency_stop = False
        self.last_heartbeat = time.time()
        self.stall_count = 0

    def report_stall(self, motor_name: str) -> bool:
        """
        Report motor stall detected

        Args:
            motor_name: Name of stalled motor

        Returns:
            True if should retry, False if max attempts reached
        """
        self.stall_count += 1
        logger.warning(f"Stall reported for {motor_name} (count: {self.stall_count})")

        if self.stall_count >= self.stall_retry_attempts:
            logger.error(f"Maximum stall retries ({self.stall_retry_attempts}) reached")
            self.trigger_emergency_stop(f"Repeated stalls on {motor_name}")
            return False

        return True

    def reset_stall_counter(self) -> None:
        """Reset stall counter after successful operation"""
        if self.stall_count > 0:
            logger.info("Resetting stall counter")
            self.stall_count = 0

    def get_status(self) -> dict:
        """
        Get current safety system status

        Returns:
            Status dictionary
        """
        current_time = time.time()

        return {
            'emergency_stop': self.emergency_stop,
            'is_safe': self.is_safe(),
            'time_since_heartbeat': current_time - self.last_heartbeat,
            'operation_time': current_time - self.start_time,
            'stall_count': self.stall_count,
            'watchdog_running': self.running,
        }

    def cleanup(self) -> None:
        """Clean shutdown of safety system"""
        logger.info("Cleaning up safety system")
        self.stop_watchdog()


if __name__ == "__main__":
    """Test safety system"""
    import yaml

    # Load config
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Test safety system
    safety = SafetySystem(config)

    logger.info("Testing safety system...")

    # Start watchdog
    safety.start_watchdog()

    # Send heartbeats
    for i in range(5):
        safety.heartbeat()
        status = safety.get_status()
        logger.info(f"Status: {status}")
        time.sleep(1.0)

    # Test emergency stop
    safety.trigger_emergency_stop("Test emergency stop")
    logger.info(f"Emergency stop: {safety.emergency_stop}")

    # Reset
    safety.reset_emergency_stop()
    logger.info(f"After reset: {safety.emergency_stop}")

    # Cleanup
    safety.cleanup()

    logger.info("Test complete")
