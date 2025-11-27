"""
Camera Interface - Arducam 8MP integration using Picamera2
Provides real-time frame capture for object detection
"""

import time
import numpy as np
from typing import Optional, Tuple
from loguru import logger

try:
    from picamera2 import Picamera2
    from libcamera import Transform
    CAMERA_AVAILABLE = True
except ImportError:
    logger.warning("Picamera2 not available - running in simulation mode")
    CAMERA_AVAILABLE = False


class CameraInterface:
    """
    Manages Arducam 8MP camera for object detection

    Handles camera initialization, frame capture, and preprocessing
    """

    def __init__(self, config: dict, simulate: bool = False):
        """
        Initialize camera interface

        Args:
            config: Camera configuration dictionary
            simulate: If True, generate test frames instead of using camera
        """
        self.config = config
        self.simulate = simulate or not CAMERA_AVAILABLE

        self.resolution = tuple(config['camera']['resolution'])
        self.framerate = config['camera']['framerate']
        self.rotation = config['camera']['rotation']

        self.camera = None
        self.frame_count = 0

        if not self.simulate:
            self._initialize_camera()
        else:
            logger.info("Camera initialized in simulation mode")

    def _initialize_camera(self) -> None:
        """Initialize Picamera2 with Arducam"""
        try:
            self.camera = Picamera2()

            # Configure camera
            camera_config = self.camera.create_still_configuration(
                main={"size": self.resolution, "format": "RGB888"},
                transform=Transform(rotation=self.rotation)
            )

            self.camera.configure(camera_config)

            # Set frame rate
            self.camera.set_controls({"FrameRate": self.framerate})

            # Start camera
            self.camera.start()

            # Allow camera to warm up
            time.sleep(2)

            logger.info(f"Arducam initialized: {self.resolution} @ {self.framerate} FPS")

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            logger.warning("Falling back to simulation mode")
            self.simulate = True
            self.camera = None

    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from camera

        Returns:
            numpy array (H, W, 3) in RGB format, or None if failed
        """
        if self.simulate:
            return self._generate_test_frame()

        try:
            # Capture frame as numpy array
            frame = self.camera.capture_array()
            self.frame_count += 1

            if frame is None:
                logger.warning("Captured frame is None")
                return None

            # Ensure RGB format
            if len(frame.shape) == 2:
                # Convert grayscale to RGB
                frame = np.stack([frame] * 3, axis=-1)

            return frame

        except Exception as e:
            logger.error(f"Frame capture failed: {e}")
            return None

    def _generate_test_frame(self) -> np.ndarray:
        """
        Generate a test frame for simulation

        Returns:
            Synthetic RGB image with grass texture
        """
        self.frame_count += 1

        # Create grass-like test image
        height, width = self.resolution[1], self.resolution[0]
        frame = np.random.randint(40, 100, (height, width, 3), dtype=np.uint8)

        # Make it greenish (grass color)
        frame[:, :, 1] += 50  # Boost green channel

        # Add a fake "poop" object for testing (brown circle)
        if self.frame_count % 30 < 15:  # Appear intermittently
            center_x = width // 2 + int(20 * np.sin(self.frame_count * 0.1))
            center_y = height // 2 + int(20 * np.cos(self.frame_count * 0.1))
            y, x = np.ogrid[:height, :width]
            mask = (x - center_x)**2 + (y - center_y)**2 <= 30**2

            frame[mask] = [80, 50, 30]  # Brown color

        return frame

    def get_frame_for_inference(self, target_size: Optional[Tuple[int, int]] = None) -> Optional[np.ndarray]:
        """
        Capture frame and resize for model inference

        Args:
            target_size: (width, height) for model input, uses config if None

        Returns:
            Resized frame ready for inference
        """
        frame = self.capture_frame()

        if frame is None:
            return None

        if target_size is None:
            target_size = tuple(self.config['vision']['inference_resolution'])

        # Resize using OpenCV (imported dynamically to avoid dependency issues)
        try:
            import cv2
            resized = cv2.resize(frame, target_size, interpolation=cv2.INTER_LINEAR)
            return resized
        except ImportError:
            # Fallback: simple numpy resize (lower quality)
            from PIL import Image
            img = Image.fromarray(frame)
            img = img.resize(target_size, Image.BILINEAR)
            return np.array(img)

    def capture_and_save(self, filepath: str) -> bool:
        """
        Capture and save frame to disk

        Args:
            filepath: Path to save image

        Returns:
            True if successful
        """
        frame = self.capture_frame()

        if frame is None:
            return False

        try:
            from PIL import Image
            img = Image.fromarray(frame)
            img.save(filepath)
            logger.info(f"Frame saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
            return False

    def get_fps(self) -> float:
        """
        Get actual capture frame rate

        Returns:
            Frames per second
        """
        if self.simulate:
            return self.framerate

        try:
            # Measure actual FPS
            start_time = time.time()
            test_frames = 10

            for _ in range(test_frames):
                self.capture_frame()

            elapsed = time.time() - start_time
            fps = test_frames / elapsed

            logger.info(f"Measured FPS: {fps:.2f}")
            return fps

        except Exception as e:
            logger.error(f"FPS measurement failed: {e}")
            return 0.0

    def cleanup(self) -> None:
        """Clean shutdown of camera"""
        if self.camera is not None:
            try:
                self.camera.stop()
                self.camera.close()
                logger.info("Camera closed successfully")
            except Exception as e:
                logger.error(f"Error closing camera: {e}")


if __name__ == "__main__":
    """Test camera interface"""
    import yaml

    # Load config
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Test camera
    camera = CameraInterface(config, simulate=True)

    logger.info("Capturing test frames...")

    for i in range(5):
        frame = camera.capture_frame()
        if frame is not None:
            logger.info(f"Frame {i+1}: shape={frame.shape}, dtype={frame.dtype}")
        time.sleep(0.5)

    # Test FPS
    fps = camera.get_fps()
    logger.info(f"Camera FPS: {fps:.2f}")

    # Save test frame
    camera.capture_and_save("test_frame.jpg")

    camera.cleanup()
    logger.info("Test complete")
