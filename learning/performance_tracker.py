"""
Performance Tracker - Real-time metrics and analytics
Tracks success rates, failure modes, and performance trends
"""

from collections import deque
from typing import Dict, List, Tuple
from loguru import logger


class PerformanceTracker:
    """
    Tracks real-time performance metrics

    Monitors success rates, failure modes, and triggers optimization
    """

    def __init__(self, config: dict, database):
        """
        Initialize performance tracker

        Args:
            config: Configuration dictionary
            database: PickupDatabase instance
        """
        self.config = config
        self.database = database

        self.rolling_window_size = config['learning']['rolling_window_size']

        # Rolling window of recent attempts
        self.recent_attempts = deque(maxlen=self.rolling_window_size)

        # Real-time counters
        self.session_attempts = 0
        self.session_successes = 0

        logger.info("Performance tracker initialized")

    def record_attempt(self, success: bool, failure_reason: Optional[str] = None) -> None:
        """
        Record pickup attempt result

        Args:
            success: Whether attempt was successful
            failure_reason: Reason for failure if unsuccessful
        """
        self.recent_attempts.append({
            'success': success,
            'failure_reason': failure_reason
        })

        self.session_attempts += 1
        if success:
            self.session_successes += 1

    def get_current_success_rate(self) -> float:
        """
        Get success rate from rolling window

        Returns:
            Success rate (0.0 to 1.0)
        """
        if len(self.recent_attempts) == 0:
            return 0.0

        successes = sum(1 for attempt in self.recent_attempts if attempt['success'])
        return successes / len(self.recent_attempts)

    def get_session_success_rate(self) -> float:
        """Get success rate for current session"""
        if self.session_attempts == 0:
            return 0.0

        return self.session_successes / self.session_attempts

    def get_failure_breakdown(self) -> Dict[str, int]:
        """
        Get counts of recent failure modes

        Returns:
            Dictionary mapping failure reasons to counts
        """
        failures = {}

        for attempt in self.recent_attempts:
            if not attempt['success'] and attempt['failure_reason']:
                reason = attempt['failure_reason']
                failures[reason] = failures.get(reason, 0) + 1

        return failures

    def should_adjust_confidence(self) -> Tuple[bool, float]:
        """
        Check if detection confidence threshold should be adjusted

        Returns:
            (should_adjust, new_threshold)
        """
        if len(self.recent_attempts) < self.rolling_window_size:
            return False, 0.0

        # Count false positives (detected but failed pickup)
        failures = self.get_failure_breakdown()
        missed_detections = failures.get('no_poop_found', 0) + failures.get('empty_scoop', 0)

        # If too many false positives, increase threshold
        if missed_detections > len(self.recent_attempts) * 0.3:  # More than 30%
            current_threshold = self.config['vision']['confidence_threshold']
            new_threshold = min(0.95, current_threshold + 0.05)
            logger.info(f"High false positive rate - suggesting threshold increase to {new_threshold:.2f}")
            return True, new_threshold

        # If very high success, can try lowering threshold
        success_rate = self.get_current_success_rate()
        if success_rate > 0.9:
            current_threshold = self.config['vision']['confidence_threshold']
            new_threshold = max(0.5, current_threshold - 0.05)
            logger.info(f"High success rate - suggesting threshold decrease to {new_threshold:.2f}")
            return True, new_threshold

        return False, 0.0

    def get_metrics_summary(self) -> Dict:
        """
        Get comprehensive metrics summary

        Returns:
            Dictionary with all metrics
        """
        return {
            'rolling_success_rate': self.get_current_success_rate(),
            'session_success_rate': self.get_session_success_rate(),
            'session_attempts': self.session_attempts,
            'session_successes': self.session_successes,
            'recent_failures': self.get_failure_breakdown(),
            'rolling_window_size': len(self.recent_attempts),
        }

    def reset_session(self) -> None:
        """Reset session counters"""
        self.session_attempts = 0
        self.session_successes = 0
        logger.info("Session counters reset")

    def get_performance_trend(self) -> str:
        """
        Get performance trend description

        Returns:
            "improving", "declining", or "stable"
        """
        if len(self.recent_attempts) < self.rolling_window_size:
            return "insufficient_data"

        # Compare first half vs second half of window
        mid = len(self.recent_attempts) // 2
        first_half = list(self.recent_attempts)[:mid]
        second_half = list(self.recent_attempts)[mid:]

        first_success = sum(1 for a in first_half if a['success']) / len(first_half)
        second_success = sum(1 for a in second_half if a['success']) / len(second_half)

        diff = second_success - first_success

        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"


if __name__ == "__main__":
    """Test performance tracker"""
    import yaml
    from pickup_database import PickupDatabase

    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    db = PickupDatabase("test_pooperscooper.db")
    tracker = PerformanceTracker(config, db)

    logger.info("Testing tracker...")

    # Simulate attempts
    for i in range(25):
        success = i % 3 != 0  # 2/3 success rate
        tracker.record_attempt(success, "dropped" if not success else None)

    metrics = tracker.get_metrics_summary()
    logger.info(f"Metrics: {metrics}")

    trend = tracker.get_performance_trend()
    logger.info(f"Trend: {trend}")

    db.close()
    logger.info("Test complete")
