"""
Position Tracker - Simple odometry for excavator position tracking
Uses dead reckoning based on movement commands and estimated speeds
"""

import time
import math
from typing import Tuple, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class Position:
    """2D position with heading"""
    x: float  # meters
    y: float  # meters
    heading: float  # radians (0 = east, pi/2 = north)
    timestamp: float


class PositionTracker:
    """
    Tracks excavator position using dead reckoning

    Since RC excavators don't have encoders, we estimate position
    based on movement commands and time
    """

    def __init__(self, config: dict):
        """
        Initialize position tracker

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Home position
        self.home_x = config['patrol']['home_position']['x']
        self.home_y = config['patrol']['home_position']['y']

        # Current position
        self.current_position = Position(
            x=self.home_x,
            y=self.home_y,
            heading=0.0,  # Facing east initially
            timestamp=time.time()
        )

        # Movement speed estimates (meters/second) - calibrate these!
        self.forward_speed = 0.3  # m/s
        self.turn_rate = math.radians(45)  # radians/second (45 deg/s)

        # Position history
        self.position_history: List[Position] = []
        self.max_history = 1000

        logger.info(f"Position tracker initialized at home ({self.home_x}, {self.home_y})")

    def update_forward(self, duration: float) -> None:
        """
        Update position after forward movement

        Args:
            duration: How long moved forward (seconds)
        """
        distance = self.forward_speed * duration

        # Calculate new position based on heading
        self.current_position.x += distance * math.cos(self.current_position.heading)
        self.current_position.y += distance * math.sin(self.current_position.heading)
        self.current_position.timestamp = time.time()

        self._add_to_history()

        logger.debug(f"Moved forward {distance:.2f}m, now at ({self.current_position.x:.2f}, {self.current_position.y:.2f})")

    def update_backward(self, duration: float) -> None:
        """Update position after backward movement"""
        distance = self.forward_speed * duration

        self.current_position.x -= distance * math.cos(self.current_position.heading)
        self.current_position.y -= distance * math.sin(self.current_position.heading)
        self.current_position.timestamp = time.time()

        self._add_to_history()

    def update_turn_left(self, duration: float) -> None:
        """Update heading after left turn"""
        angle_change = self.turn_rate * duration
        self.current_position.heading += angle_change
        self.current_position.heading = self._normalize_angle(self.current_position.heading)
        self.current_position.timestamp = time.time()

        logger.debug(f"Turned left, heading now {math.degrees(self.current_position.heading):.1f}°")

    def update_turn_right(self, duration: float) -> None:
        """Update heading after right turn"""
        angle_change = self.turn_rate * duration
        self.current_position.heading -= angle_change
        self.current_position.heading = self._normalize_angle(self.current_position.heading)
        self.current_position.timestamp = time.time()

    def _normalize_angle(self, angle: float) -> float:
        """Normalize angle to [-pi, pi]"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle

    def _add_to_history(self) -> None:
        """Add current position to history"""
        self.position_history.append(Position(
            x=self.current_position.x,
            y=self.current_position.y,
            heading=self.current_position.heading,
            timestamp=self.current_position.timestamp
        ))

        # Limit history size
        if len(self.position_history) > self.max_history:
            self.position_history.pop(0)

    def get_current_position(self) -> Tuple[float, float]:
        """
        Get current position

        Returns:
            (x, y) in meters
        """
        return (self.current_position.x, self.current_position.y)

    def get_current_heading(self) -> float:
        """Get current heading in radians"""
        return self.current_position.heading

    def distance_to_home(self) -> float:
        """
        Calculate distance to home position

        Returns:
            Distance in meters
        """
        dx = self.home_x - self.current_position.x
        dy = self.home_y - self.current_position.y
        return math.sqrt(dx**2 + dy**2)

    def heading_to_home(self) -> float:
        """
        Calculate heading angle to home position

        Returns:
            Angle in radians
        """
        dx = self.home_x - self.current_position.x
        dy = self.home_y - self.current_position.y
        return math.atan2(dy, dx)

    def turn_angle_to_home(self) -> float:
        """
        Calculate turn angle needed to face home

        Returns:
            Angle to turn (radians, positive = left, negative = right)
        """
        target_heading = self.heading_to_home()
        turn_angle = target_heading - self.current_position.heading
        return self._normalize_angle(turn_angle)

    def distance_to_point(self, x: float, y: float) -> float:
        """Calculate distance to specific point"""
        dx = x - self.current_position.x
        dy = y - self.current_position.y
        return math.sqrt(dx**2 + dy**2)

    def heading_to_point(self, x: float, y: float) -> float:
        """Calculate heading to specific point"""
        dx = x - self.current_position.x
        dy = y - self.current_position.y
        return math.atan2(dy, dx)

    def reset_to_home(self) -> None:
        """Reset position to home (for calibration/correction)"""
        logger.info("Resetting position to home")
        self.current_position.x = self.home_x
        self.current_position.y = self.home_y
        self.current_position.heading = 0.0
        self.current_position.timestamp = time.time()

    def set_position(self, x: float, y: float, heading: Optional[float] = None) -> None:
        """
        Manually set position (for visual correction)

        Args:
            x: X coordinate (meters)
            y: Y coordinate (meters)
            heading: Optional heading (radians)
        """
        self.current_position.x = x
        self.current_position.y = y
        if heading is not None:
            self.current_position.heading = self._normalize_angle(heading)
        self.current_position.timestamp = time.time()

        logger.info(f"Position manually set to ({x:.2f}, {y:.2f})")

    def get_position_history(self) -> List[Tuple[float, float]]:
        """
        Get position history as list of (x, y) tuples

        Returns:
            List of positions
        """
        return [(p.x, p.y) for p in self.position_history]

    def calibrate_speeds(self, forward_speed: float, turn_rate_deg_per_sec: float) -> None:
        """
        Calibrate movement speeds

        Args:
            forward_speed: Forward speed in m/s
            turn_rate_deg_per_sec: Turn rate in degrees/second
        """
        self.forward_speed = forward_speed
        self.turn_rate = math.radians(turn_rate_deg_per_sec)

        logger.info(f"Speeds calibrated: forward={forward_speed:.2f} m/s, turn={turn_rate_deg_per_sec:.1f}°/s")


if __name__ == "__main__":
    """Test position tracker"""
    import yaml

    # Load config
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    tracker = PositionTracker(config)

    logger.info("Testing position tracking...")

    # Simulate movement sequence
    tracker.update_forward(2.0)  # Move forward 2 seconds
    logger.info(f"Position: {tracker.get_current_position()}")

    tracker.update_turn_left(1.0)  # Turn left 1 second
    logger.info(f"Heading: {math.degrees(tracker.get_current_heading()):.1f}°")

    tracker.update_forward(3.0)  # Move forward 3 seconds
    logger.info(f"Position: {tracker.get_current_position()}")

    # Check distance to home
    dist = tracker.distance_to_home()
    logger.info(f"Distance to home: {dist:.2f}m")

    # Calculate turn needed to face home
    turn_angle = tracker.turn_angle_to_home()
    logger.info(f"Turn angle to face home: {math.degrees(turn_angle):.1f}°")

    logger.info("Test complete")
