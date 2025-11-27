"""Hardware control module for excavator and sensors."""

from .excavator import ExcavatorController
from .audio_monitor import AudioMonitor

__all__ = ['ExcavatorController', 'AudioMonitor']
