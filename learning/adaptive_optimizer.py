"""
Adaptive Optimizer - Machine learning for pickup parameter optimization
Uses success data to automatically improve arm timing and approach strategies
"""

import numpy as np
from typing import Dict, Optional
from loguru import logger


class AdaptiveOptimizer:
    """
    Optimizes pickup parameters based on success/failure data

    Uses simple Bayesian-like optimization with epsilon-greedy exploration
    """

    def __init__(self, config: dict, database):
        """
        Initialize optimizer

        Args:
            config: Configuration dictionary
            database: PickupDatabase instance
        """
        self.config = config
        self.database = database

        self.enabled = config['learning']['enabled']
        self.min_attempts = config['learning']['min_attempts_before_learning']
        self.success_threshold = config['learning']['success_rate_threshold']
        self.adjustment_rate = config['learning']['parameter_adjustment_rate']
        self.exploration_rate = config['learning']['exploration_rate']

        # Current parameters
        self.current_timings = {
            'boom_up': config['timing']['boom_up_full'],
            'boom_down': config['timing']['boom_down_full'],
            'arm_up': config['timing']['arm_up_full'],
            'arm_down': config['timing']['arm_down_full'],
            'bucket_scoop': config['timing']['bucket_scoop'],
        }

        logger.info(f"Adaptive optimizer initialized ({'enabled' if self.enabled else 'disabled'})")

    def should_optimize(self) -> bool:
        """Check if we should trigger optimization"""
        if not self.enabled:
            return False

        stats = self.database.get_statistics()
        total_attempts = stats['total_attempts']

        if total_attempts < self.min_attempts:
            return False

        success_rate = self.database.get_success_rate(last_n=self.config['learning']['rolling_window_size'])

        return success_rate < self.success_threshold

    def optimize_parameters(self) -> Dict[str, float]:
        """
        Optimize pickup parameters based on success data

        Returns:
            Dictionary of optimized parameters
        """
        if not self.should_optimize():
            return self.current_timings

        logger.info("Optimizing parameters...")

        # Get best timings from successful attempts
        best_timings = self.database.get_best_arm_timings()

        if not best_timings:
            logger.warning("No successful attempts to learn from")
            return self.current_timings

        # Blend current timings with best timings
        for param in self.current_timings:
            if param in best_timings and best_timings[param] is not None:
                current = self.current_timings[param]
                best = best_timings[param]

                # Move toward best timing
                new_value = current + self.adjustment_rate * (best - current)
                self.current_timings[param] = new_value

                logger.info(f"  {param}: {current:.2f} -> {new_value:.2f}")

        return self.current_timings

    def get_timing_with_exploration(self, param_name: str) -> float:
        """
        Get parameter value with epsilon-greedy exploration

        Args:
            param_name: Parameter name

        Returns:
            Parameter value (with possible exploration)
        """
        base_value = self.current_timings.get(param_name, 1.0)

        # Epsilon-greedy: explore with small probability
        if np.random.random() < self.exploration_rate:
            # Explore: add random variation (±20%)
            variation = np.random.uniform(-0.2, 0.2)
            explored_value = base_value * (1 + variation)
            logger.debug(f"Exploring {param_name}: {explored_value:.2f} (base: {base_value:.2f})")
            return max(0.1, explored_value)  # Ensure positive

        return base_value

    def get_all_timings(self, explore: bool = True) -> Dict[str, float]:
        """
        Get all arm timing parameters

        Args:
            explore: Whether to use exploration

        Returns:
            Dictionary of timing parameters
        """
        if explore and self.enabled:
            return {
                param: self.get_timing_with_exploration(param)
                for param in self.current_timings
            }
        else:
            return self.current_timings.copy()

    def save_learned_parameters(self) -> None:
        """Save current parameters to database"""
        stats = self.database.get_statistics()
        success_rate = stats['success_rate']
        attempts = stats['total_attempts']

        for param, value in self.current_timings.items():
            self.database.save_learned_parameter(param, value, success_rate, attempts)

        logger.info("Learned parameters saved to database")

    def load_learned_parameters(self) -> bool:
        """
        Load learned parameters from database

        Returns:
            True if parameters were loaded
        """
        loaded = False

        for param in self.current_timings:
            value = self.database.get_learned_parameter(param)
            if value is not None:
                self.current_timings[param] = value
                loaded = True

        if loaded:
            logger.info("Loaded learned parameters from database")

        return loaded


if __name__ == "__main__":
    """Test adaptive optimizer"""
    from pickup_database import PickupDatabase
    import yaml

    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    db = PickupDatabase("test_pooperscooper.db")
    optimizer = AdaptiveOptimizer(config, db)

    logger.info("Testing optimizer...")

    # Log some attempts
    session_id = db.start_patrol_session("test")

    for i in range(15):
        success = i % 4 != 0  # 75% success
        db.log_pickup_attempt(
            success=success,
            arm_timings=optimizer.get_all_timings(explore=True),
            session_id=session_id
        )

    # Try optimization
    if optimizer.should_optimize():
        optimized = optimizer.optimize_parameters()
        logger.info(f"Optimized timings: {optimized}")

    db.close()
    logger.info("Test complete")
