"""
Audio Monitor - FFT-based motor stall detection
Listens to excavator motor sounds and detects anomalies indicating stalls

HOW TO TUNE STALL DETECTION:
================================
1. CALIBRATION (run once per motor):
   - Run: python main.py --calibrate-audio
   - Activate each motor for 5 seconds
   - System records baseline frequency (typically 200-800 Hz)
   - Saves to models/audio_calibration.json

2. TUNING PARAMETERS in config.yaml:

   audio:
     stall_frequency_threshold: 100  # TUNE THIS
       # Absolute minimum Hz - any frequency below this is a stall
       # TOO LOW (< 50): Won't detect stalls
       # TOO HIGH (> 200): False positives on normal operation
       # RECOMMENDED: Start at 100, decrease if missing stalls

     frequency_drop_percent: 50  # TUNE THIS
       # Percent drop from baseline to trigger stall
       # TOO LOW (< 30%): Too sensitive, false positives
       # TOO HIGH (> 70%): Won't detect until severe stall
       # RECOMMENDED: Start at 50%, adjust based on testing

3. TESTING:
   - Deliberately cause a stall (push excavator against ground)
   - Check logs for "STALL DETECTED" message
   - If not detected: DECREASE both thresholds by 10-20%
   - If too many false positives: INCREASE thresholds by 10-20%

4. RETRY STRATEGIES (when stall detected):
   - System will automatically try different approaches
   - See StallRetryStrategy enum below for retry methods
"""

import time
import numpy as np
from typing import Optional, Dict, List, Callable
from collections import deque
from enum import Enum
from loguru import logger

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    logger.warning("sounddevice not available - audio monitoring disabled")
    AUDIO_AVAILABLE = False


class StallRetryStrategy(Enum):
    """Retry strategies when stall is detected"""
    BACK_UP = "back_up"          # Reverse briefly, try again
    ADJUST_ANGLE = "adjust_angle"  # Turn slightly, approach from different angle
    REDUCE_DEPTH = "reduce_depth"  # Use shallower scoop
    INCREASE_FORCE = "increase_force"  # Hold button longer for more force
    SKIP = "skip"                 # Give up on this target


class AudioMonitor:
    """
    Monitors motor sounds to detect stalls using FFT analysis

    A motor stall produces characteristic changes in frequency spectrum:
    - Decrease in primary motor frequency
    - Increase in low-frequency harmonics
    - Overall amplitude changes
    """

    def __init__(self, config: dict, simulate: bool = False):
        """
        Initialize audio monitoring

        Args:
            config: Audio configuration dictionary
            simulate: If True, generate simulated audio data
        """
        self.config = config
        self.simulate = simulate or not AUDIO_AVAILABLE

        self.sample_rate = config['audio']['sample_rate']
        self.channels = config['audio']['channels']
        self.window_duration = config['audio']['window_duration']
        self.stall_threshold = config['audio']['stall_frequency_threshold']
        self.frequency_drop_percent = config['audio']['frequency_drop_percent']

        # Baseline frequency profiles for each motor
        self.baseline_frequencies: Dict[str, float] = {}

        # Recent measurements for filtering
        self.measurement_history = deque(maxlen=10)

        # Stall detection state
        self.stall_detected = False
        self.current_motor = None

        # Retry strategy tracking
        self.retry_attempts = 0
        self.max_retries = 3
        self.retry_callback: Optional[Callable] = None

        logger.info(f"Audio monitor initialized ({'simulated' if self.simulate else 'hardware'} mode)")

    def calibrate_motor(self, motor_name: str, duration: float = 5.0) -> bool:
        """
        Record baseline frequency for a specific motor

        Args:
            motor_name: Name of motor being calibrated
            duration: Recording duration in seconds

        Returns:
            True if calibration successful
        """
        logger.info(f"Calibrating motor '{motor_name}' for {duration}s...")

        try:
            # Record multiple samples
            samples = []
            num_samples = int(duration / self.window_duration)

            for i in range(num_samples):
                freq = self._get_dominant_frequency()
                if freq is not None:
                    samples.append(freq)
                    logger.debug(f"Sample {i+1}/{num_samples}: {freq:.1f} Hz")

                time.sleep(self.window_duration)

            if len(samples) < num_samples // 2:
                logger.error(f"Calibration failed - insufficient samples")
                return False

            # Calculate median frequency (robust to outliers)
            baseline = np.median(samples)
            self.baseline_frequencies[motor_name] = baseline

            logger.info(f"Motor '{motor_name}' baseline: {baseline:.1f} Hz")
            return True

        except Exception as e:
            logger.error(f"Calibration error: {e}")
            return False

    def _get_dominant_frequency(self) -> Optional[float]:
        """
        Capture audio and analyze dominant frequency

        Returns:
            Dominant frequency in Hz, or None if failed
        """
        if self.simulate:
            return self._simulate_frequency()

        try:
            # Record audio window
            samples_per_window = int(self.sample_rate * self.window_duration)
            audio_data = sd.rec(
                samples_per_window,
                samplerate=self.sample_rate,
                channels=self.channels,
                blocking=True
            )

            # Flatten to 1D if stereo
            if audio_data.ndim > 1:
                audio_data = audio_data[:, 0]

            # Compute FFT
            fft_result = np.fft.fft(audio_data.flatten())
            frequencies = np.fft.fftfreq(len(fft_result), 1.0 / self.sample_rate)

            # Only consider positive frequencies
            positive_freqs = frequencies[:len(frequencies)//2]
            positive_fft = np.abs(fft_result[:len(fft_result)//2])

            # Find dominant frequency
            dominant_idx = np.argmax(positive_fft)
            dominant_freq = positive_freqs[dominant_idx]

            return abs(dominant_freq)

        except Exception as e:
            logger.error(f"Frequency analysis failed: {e}")
            return None

    def _simulate_frequency(self) -> float:
        """
        Generate simulated frequency data for testing

        Returns:
            Simulated dominant frequency
        """
        # Simulate normal motor frequency with noise
        base_freq = 400.0 + np.random.normal(0, 20)

        # Occasionally simulate stall
        if np.random.random() < 0.05:  # 5% chance of stall
            base_freq = 60.0 + np.random.normal(0, 10)
            logger.debug("[SIMULATED STALL]")

        return base_freq

    def check_for_stall(self, motor_name: str) -> bool:
        """
        Check if motor is stalling

        Args:
            motor_name: Name of motor to monitor

        Returns:
            True if stall detected
        """
        self.current_motor = motor_name

        # Get current frequency
        current_freq = self._get_dominant_frequency()

        if current_freq is None:
            logger.warning("Could not get frequency - assuming no stall")
            return False

        # Add to history
        self.measurement_history.append(current_freq)

        # Check if motor was calibrated
        if motor_name not in self.baseline_frequencies:
            logger.warning(f"Motor '{motor_name}' not calibrated - using default threshold")
            baseline = 400.0  # Typical motor frequency
        else:
            baseline = self.baseline_frequencies[motor_name]

        # Detect stall conditions
        stall_condition_1 = current_freq < self.stall_threshold
        stall_condition_2 = current_freq < baseline * (1 - self.frequency_drop_percent / 100)

        is_stalled = stall_condition_1 or stall_condition_2

        if is_stalled:
            logger.warning(f"STALL DETECTED: {motor_name} at {current_freq:.1f} Hz (baseline: {baseline:.1f} Hz)")
            self.stall_detected = True
        else:
            self.stall_detected = False
            logger.debug(f"Motor OK: {current_freq:.1f} Hz")

        return is_stalled

    def get_frequency_history(self) -> List[float]:
        """
        Get recent frequency measurements

        Returns:
            List of recent frequencies
        """
        return list(self.measurement_history)

    def reset_stall_flag(self) -> None:
        """Clear stall detection flag"""
        self.stall_detected = False
        self.current_motor = None
        self.retry_attempts = 0

    def get_retry_strategy(self) -> StallRetryStrategy:
        """
        Determine which retry strategy to use based on retry count

        Returns:
            StallRetryStrategy enum value
        """
        if self.retry_attempts == 0:
            return StallRetryStrategy.BACK_UP
        elif self.retry_attempts == 1:
            return StallRetryStrategy.ADJUST_ANGLE
        elif self.retry_attempts == 2:
            return StallRetryStrategy.REDUCE_DEPTH
        else:
            return StallRetryStrategy.SKIP

    def handle_stall(self, motor_name: str) -> StallRetryStrategy:
        """
        Handle stall detection - determine retry strategy

        Args:
            motor_name: Name of stalled motor

        Returns:
            Strategy to retry with
        """
        self.retry_attempts += 1
        strategy = self.get_retry_strategy()

        logger.warning(f"Stall on {motor_name} - Retry #{self.retry_attempts}: {strategy.value}")

        return strategy

    def save_calibration(self, filepath: str) -> bool:
        """
        Save baseline frequencies to file

        Args:
            filepath: Path to save calibration data

        Returns:
            True if successful
        """
        try:
            import json

            data = {
                'baseline_frequencies': self.baseline_frequencies,
                'sample_rate': self.sample_rate,
                'stall_threshold': self.stall_threshold
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Calibration saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save calibration: {e}")
            return False

    def load_calibration(self, filepath: str) -> bool:
        """
        Load baseline frequencies from file

        Args:
            filepath: Path to calibration file

        Returns:
            True if successful
        """
        try:
            import json

            with open(filepath, 'r') as f:
                data = json.load(f)

            self.baseline_frequencies = data['baseline_frequencies']
            logger.info(f"Calibration loaded: {self.baseline_frequencies}")
            return True

        except Exception as e:
            logger.error(f"Failed to load calibration: {e}")
            return False
