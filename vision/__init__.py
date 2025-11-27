"""Vision processing module for object detection and marker recognition."""

from .detector import PoopDetector
from .camera import CameraInterface
from .marker_detection import RedFlagDetector

__all__ = ['PoopDetector', 'CameraInterface', 'RedFlagDetector']
