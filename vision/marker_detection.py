"""
Red Flag Marker Detection - Visual marker for disposal location
Uses HSV color space to detect red flag for navigation
"""

import numpy as np
from typing import Optional, Tuple
from loguru import logger

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    logger.warning("OpenCV not available - marker detection disabled")
    CV2_AVAILABLE = False


class RedFlagDetector:
    """
    Detects red flag marker for disposal location

    Uses HSV color segmentation to find red objects in frame
    """

    def __init__(self, config: dict, simulate: bool = False):
        """
        Initialize red flag detector

        Args:
            config: Vision configuration dictionary
            simulate: If True, generate fake marker positions
        """
        self.config = config
        self.simulate = simulate or not CV2_AVAILABLE

        # HSV color range for red
        self.hsv_lower = np.array(config['vision']['red_flag_hsv_lower'])
        self.hsv_upper = np.array(config['vision']['red_flag_hsv_upper'])

        # Additional red range (red wraps around in HSV)
        self.hsv_lower2 = np.array([170, 100, 100])
        self.hsv_upper2 = np.array([180, 255, 255])

        self.min_area = 500  # Minimum contour area in pixels

        logger.info(f"Red flag detector initialized ({'simulated' if self.simulate else 'hardware'} mode)")

    def detect_flag(self, image: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Detect red flag in image

        Args:
            image: RGB image as numpy array

        Returns:
            (x, y) center of flag, or None if not found
        """
        if self.simulate:
            return self._simulate_flag_detection(image)

        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available")
            return None

        try:
            # Convert to HSV color space
            hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

            # Create mask for red color (two ranges since red wraps around)
            mask1 = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)
            mask2 = cv2.inRange(hsv, self.hsv_lower2, self.hsv_upper2)
            mask = cv2.bitwise_or(mask1, mask2)

            # Apply morphological operations to clean up mask
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if len(contours) == 0:
                return None

            # Find largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)

            if area < self.min_area:
                logger.debug(f"Red area too small: {area} pixels")
                return None

            # Calculate center
            M = cv2.moments(largest_contour)
            if M['m00'] == 0:
                return None

            center_x = int(M['m10'] / M['m00'])
            center_y = int(M['m01'] / M['m00'])

            logger.debug(f"Red flag detected at ({center_x}, {center_y}), area={area}")

            return (center_x, center_y)

        except Exception as e:
            logger.error(f"Flag detection failed: {e}")
            return None

    def _simulate_flag_detection(self, image: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Simulate flag detection for testing

        Args:
            image: Input image

        Returns:
            Simulated flag position
        """
        h, w = image.shape[:2]

        # Randomly detect flag 80% of the time
        if np.random.random() < 0.8:
            # Place flag in random location (simulating flag in view)
            x = np.random.randint(w // 4, 3 * w // 4)
            y = np.random.randint(h // 4, 3 * h // 4)
            return (x, y)

        return None

    def get_direction_to_flag(
        self,
        flag_position: Tuple[int, int],
        image_shape: Tuple[int, int]
    ) -> str:
        """
        Determine direction to navigate toward flag

        Args:
            flag_position: (x, y) position of flag in image
            image_shape: (height, width) of image

        Returns:
            Direction string: "left", "right", "forward", "centered"
        """
        h, w = image_shape[:2]
        center_x = w // 2
        flag_x, flag_y = flag_position

        # Define threshold for "centered"
        threshold = w // 10

        if flag_x < center_x - threshold:
            return "left"
        elif flag_x > center_x + threshold:
            return "right"
        else:
            # Check if flag is large enough (close)
            # If flag is centered and large, we're at destination
            return "centered"

    def estimate_distance(
        self,
        flag_position: Tuple[int, int],
        image_shape: Tuple[int, int]
    ) -> float:
        """
        Estimate rough distance to flag based on vertical position

        Args:
            flag_position: (x, y) position of flag
            image_shape: (height, width) of image

        Returns:
            Estimated distance in arbitrary units (higher = further)
        """
        h, w = image_shape[:2]
        flag_x, flag_y = flag_position

        # Simple heuristic: lower in image = closer
        # Normalize to 0-1 range (0 = very close, 1 = far)
        distance_estimate = flag_y / h

        return distance_estimate

    def draw_detection(
        self,
        image: np.ndarray,
        flag_position: Optional[Tuple[int, int]]
    ) -> np.ndarray:
        """
        Draw flag detection on image for visualization

        Args:
            image: Input image
            flag_position: Position of detected flag

        Returns:
            Image with detection drawn
        """
        if not CV2_AVAILABLE or flag_position is None:
            return image

        try:
            # Draw circle at flag position
            output = image.copy()
            cv2.circle(output, flag_position, 20, (0, 255, 0), 3)
            cv2.circle(output, flag_position, 5, (0, 255, 0), -1)

            # Draw text
            cv2.putText(
                output,
                "FLAG",
                (flag_position[0] + 25, flag_position[1]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            return output

        except Exception as e:
            logger.error(f"Draw detection failed: {e}")
            return image


if __name__ == "__main__":
    """Test red flag detector"""
    import yaml

    # Load config
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Test detector
    detector = RedFlagDetector(config, simulate=True)

    logger.info("Testing red flag detection...")

    # Create test image
    test_image = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

    # Run detection
    for i in range(5):
        flag_pos = detector.detect_flag(test_image)

        if flag_pos:
            direction = detector.get_direction_to_flag(flag_pos, test_image.shape[:2])
            distance = detector.estimate_distance(flag_pos, test_image.shape[:2])

            logger.info(f"Test {i+1}: Flag at {flag_pos}, direction={direction}, distance={distance:.2f}")
        else:
            logger.info(f"Test {i+1}: No flag detected")

    logger.info("Test complete")
