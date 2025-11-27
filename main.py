"""
Pooper Scooper Main Entry Point
Autonomous RC excavator for dog poop cleanup
"""

import sys
import signal
import yaml
from pathlib import Path
from loguru import logger

# Import modules
from utils.logging_setup import setup_logging
from hardware.excavator import ExcavatorController
from hardware.audio_monitor import AudioMonitor
from vision.camera import CameraInterface
from vision.detector import PoopDetector
from vision.marker_detection import RedFlagDetector
from control.state_machines import NavigationStateMachine, ManipulationStateMachine
from control.behavior_tree import PooperScooperBehaviorTree
from control.patrol_planner import PatrolPlanner
from safety.watchdog import SafetySystem
from utils.position_tracker import PositionTracker
from learning.pickup_database import PickupDatabase
from learning.adaptive_optimizer import AdaptiveOptimizer
from learning.performance_tracker import PerformanceTracker
from navigation.map_manager import MapManager
from navigation.path_planner import PathPlanner
import threading


class PooperScooperSystem:
    """Main system coordinator"""

    def __init__(self, config_path: str = "config.yaml", simulate: bool = False):
        """
        Initialize the complete system

        Args:
            config_path: Path to configuration file
            simulate: If True, run in simulation mode (no hardware)
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Setup logging
        setup_logging(self.config)

        logger.info("=" * 60)
        logger.info("POOPER SCOOPER - Autonomous Dog Waste Cleanup System")
        logger.info("=" * 60)

        self.simulate = simulate

        if self.simulate:
            logger.warning("Running in SIMULATION mode")

        # Initialize hardware components
        logger.info("Initializing hardware...")
        self.excavator = ExcavatorController(self.config, simulate=simulate)
        self.audio_monitor = AudioMonitor(self.config, simulate=simulate)

        # Initialize vision components
        logger.info("Initializing vision...")
        self.camera = CameraInterface(self.config, simulate=simulate)
        self.detector = PoopDetector(self.config, simulate=simulate)
        self.flag_detector = RedFlagDetector(self.config, simulate=simulate)

        # Initialize control systems
        logger.info("Initializing control systems...")
        self.nav_sm = NavigationStateMachine()
        self.arm_sm = ManipulationStateMachine()

        # Initialize safety system
        logger.info("Initializing safety systems...")
        self.safety = SafetySystem(self.config)

        # Initialize learning and navigation modules
        logger.info("Initializing learning and navigation systems...")
        self.database = PickupDatabase(self.config['learning']['database_path'])
        self.position_tracker = PositionTracker(self.config)
        self.patrol_planner = PatrolPlanner(self.config)
        self.optimizer = AdaptiveOptimizer(self.config, self.database)
        self.performance_tracker = PerformanceTracker(self.database)
        self.map_manager = MapManager(self.config, self.database)
        self.path_planner = PathPlanner(self.config)

        # Initialize behavior tree
        logger.info("Building behavior tree...")
        self.behavior_tree = PooperScooperBehaviorTree(
            excavator=self.excavator,
            camera=self.camera,
            detector=self.detector,
            flag_detector=self.flag_detector,
            audio_monitor=self.audio_monitor,
            nav_sm=self.nav_sm,
            arm_sm=self.arm_sm,
            safety=self.safety,
            patrol_planner=self.patrol_planner,
            position_tracker=self.position_tracker,
            database=self.database,
            optimizer=self.optimizer,
            map_manager=self.map_manager
        )

        # Start web server in background thread
        logger.info("Starting web interface...")
        self._start_web_server()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("System initialization complete!")

    def _start_web_server(self) -> None:
        """Start Flask web server in background thread"""
        try:
            from web.app import run_app, set_system_reference

            # Pass system reference to web app for control
            set_system_reference(self)

            # Start server in daemon thread
            self.web_thread = threading.Thread(
                target=run_app,
                args=('0.0.0.0', 5000),
                daemon=True
            )
            self.web_thread.start()

            logger.info("Web interface started on http://0.0.0.0:5000")
        except ImportError as e:
            logger.warning(f"Web interface not available: {e}")
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")

    def start_patrol_from_web(self) -> None:
        """Start patrol command from web interface"""
        logger.info("Patrol command received from web interface")
        self.behavior_tree.blackboard.patrol_active = True

    def stop_patrol_from_web(self) -> None:
        """Stop patrol command from web interface"""
        logger.info("Stop patrol command received from web interface")
        self.behavior_tree.blackboard.patrol_active = False

    def return_home_from_web(self) -> None:
        """Return home command from web interface"""
        logger.info("Return home command received from web interface")
        self.behavior_tree.blackboard.patrol_active = False
        # Trigger return home sequence

    def get_status(self) -> dict:
        """Get current system status for web interface"""
        status = {
            'patrol_active': self.behavior_tree.blackboard.patrol_active,
            'pickup_count': self.behavior_tree.blackboard.pickup_count,
            'nav_state': self.nav_sm.state if hasattr(self.nav_sm, 'state') else 'unknown',
            'arm_state': self.arm_sm.state if hasattr(self.arm_sm, 'state') else 'unknown',
            'emergency_stop': self.safety.emergency_stop,
        }

        # Add position if available
        if self.position_tracker:
            pos = self.position_tracker.get_current_position()
            status['position'] = {
                'x': pos.x,
                'y': pos.y,
                'heading': pos.heading
            }

        # Add coverage if available
        if self.patrol_planner:
            status['coverage'] = self.patrol_planner.get_coverage_percentage()

        return status

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.warning(f"Received signal {signum} - initiating shutdown")
        self.shutdown()
        sys.exit(0)

    def calibrate_audio(self) -> None:
        """
        Calibrate audio monitoring for motor baselines

        Run this once before first use or when motors change
        """
        logger.info("Starting audio calibration...")
        logger.info("Run each motor for 5 seconds during calibration")

        motors_to_calibrate = [
            ("boom_motor", "boom_up"),
            ("arm_motor", "arm_up"),
            ("bucket_motor", "bucket_in"),
            ("drive_motor", "move_forward"),
        ]

        for motor_name, control_name in motors_to_calibrate:
            logger.info(f"\nCalibrating {motor_name}...")
            logger.info(f"Press Enter to start {motor_name} calibration")
            input()

            # Activate motor
            control = getattr(self.excavator, control_name.replace('_', '_').split('_')[0] + '_' + control_name.split('_')[1])
            if hasattr(self.excavator, control_name):
                # Run motor while calibrating
                import threading

                def run_motor():
                    getattr(self.excavator, control_name)(5.0)

                thread = threading.Thread(target=run_motor)
                thread.start()

                # Calibrate
                self.audio_monitor.calibrate_motor(motor_name, duration=5.0)

                thread.join()

        # Save calibration
        calibration_file = "models/audio_calibration.json"
        Path(calibration_file).parent.mkdir(exist_ok=True)
        self.audio_monitor.save_calibration(calibration_file)

        logger.info(f"Calibration complete and saved to {calibration_file}")

    def calibrate_home_position(self) -> bool:
        """
        Calibrate excavator home position using stall detection

        Returns:
            True if calibration successful
        """
        logger.info("Initiating home position calibration...")
        success = self.excavator.calibrate_home_position(
            audio_monitor=self.audio_monitor,
            max_duration=10.0
        )

        if success:
            logger.info("Home position calibration successful")
        else:
            logger.warning("Home position calibration incomplete - check logs")

        return success

    def run(self, max_iterations: int = 1000) -> None:
        """
        Run the main control loop

        Args:
            max_iterations: Maximum iterations before auto-shutdown
        """
        logger.info("Starting main control loop...")

        try:
            # Start safety watchdog
            self.safety.start_watchdog()

            # STEP 1: Calibrate home position using stall detection
            logger.info("=" * 60)
            logger.info("STEP 1: Calibrating home position")
            logger.info("=" * 60)

            if not self.calibrate_home_position():
                logger.error("Home position calibration failed!")
                logger.warning("System may still operate but position tracking will be inaccurate")
                logger.info("Continue anyway? (y/n)")
                response = input().strip().lower()
                if response != 'y':
                    logger.info("Aborting startup")
                    return

            # STEP 2: Start behavior tree
            logger.info("=" * 60)
            logger.info("STEP 2: Starting autonomous operation")
            logger.info("=" * 60)

            self.behavior_tree.run(max_iterations=max_iterations)

        except KeyboardInterrupt:
            logger.warning("Interrupted by user")

        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            self.safety.trigger_emergency_stop(f"Exception: {e}")

        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Clean shutdown of all systems"""
        logger.info("Shutting down system...")

        # Stop all movement
        self.excavator.stop_all()

        # Return to home position (if safe)
        if not self.safety.emergency_stop:
            logger.info("Returning to home position...")
            try:
                self.excavator.home_position()
            except Exception as e:
                logger.error(f"Failed to return home: {e}")

        # Cleanup components
        self.safety.cleanup()
        self.camera.cleanup()
        self.excavator.cleanup()

        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Pooper Scooper - Autonomous Dog Waste Cleanup")
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to configuration file')
    parser.add_argument('--simulate', action='store_true', help='Run in simulation mode (no hardware)')
    parser.add_argument('--calibrate-audio', action='store_true', help='Run audio calibration')
    parser.add_argument('--calibrate-home', action='store_true', help='Run home position calibration only')
    parser.add_argument('--max-iterations', type=int, default=1000, help='Maximum control loop iterations')

    args = parser.parse_args()

    # Create system
    system = PooperScooperSystem(config_path=args.config, simulate=args.simulate)

    # Run audio calibration if requested
    if args.calibrate_audio:
        system.calibrate_audio()
        return

    # Run home position calibration if requested
    if args.calibrate_home:
        logger.info("Running home position calibration only")
        success = system.calibrate_home_position()
        if success:
            logger.info("✓ Calibration successful - excavator at home position")
        else:
            logger.warning("⚠ Calibration incomplete - check logs for details")
        return

    # Run main loop
    system.run(max_iterations=args.max_iterations)


if __name__ == "__main__":
    main()
