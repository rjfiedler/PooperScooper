"""
Behavior Tree for Pooper Scooper
Main control logic using py_trees framework
"""

import time
import py_trees
from py_trees.common import Status
from loguru import logger
from typing import Any, Optional


class PooperScooperBehaviorTree:
    """
    Main behavior tree for autonomous excavator operation

    Coordinates vision, navigation, manipulation, and safety with patrol and learning
    """

    def __init__(self, excavator, camera, detector, flag_detector, audio_monitor, nav_sm, arm_sm, safety,
                 patrol_planner=None, position_tracker=None, database=None, optimizer=None, map_manager=None):
        """
        Initialize behavior tree

        Args:
            excavator: ExcavatorController instance
            camera: CameraInterface instance
            detector: PoopDetector instance
            flag_detector: RedFlagDetector instance
            audio_monitor: AudioMonitor instance
            nav_sm: NavigationStateMachine instance
            arm_sm: ManipulationStateMachine instance
            safety: SafetySystem instance
            patrol_planner: PatrolPlanner instance (optional)
            position_tracker: PositionTracker instance (optional)
            database: PickupDatabase instance (optional)
            optimizer: AdaptiveOptimizer instance (optional)
            map_manager: MapManager instance (optional)
        """
        self.excavator = excavator
        self.camera = camera
        self.detector = detector
        self.flag_detector = flag_detector
        self.audio_monitor = audio_monitor
        self.nav_sm = nav_sm
        self.arm_sm = arm_sm
        self.safety = safety

        # Learning and patrol modules
        self.patrol_planner = patrol_planner
        self.position_tracker = position_tracker
        self.database = database
        self.optimizer = optimizer
        self.map_manager = map_manager

        # Shared blackboard for data exchange
        self.blackboard = py_trees.blackboard.Client(name="PooperScooper")
        self.blackboard.register_key(key="current_target", access=py_trees.common.Access.WRITE)
        self.blackboard.register_key(key="flag_position", access=py_trees.common.Access.WRITE)
        self.blackboard.register_key(key="pickup_count", access=py_trees.common.Access.WRITE)
        self.blackboard.register_key(key="patrol_active", access=py_trees.common.Access.WRITE)
        self.blackboard.register_key(key="current_waypoint", access=py_trees.common.Access.WRITE)
        self.blackboard.register_key(key="session_id", access=py_trees.common.Access.WRITE)

        self.blackboard.current_target = None
        self.blackboard.flag_position = None
        self.blackboard.pickup_count = 0
        self.blackboard.patrol_active = False
        self.blackboard.current_waypoint = None
        self.blackboard.session_id = None

        # Build behavior tree
        self.root = self._build_tree()

        logger.info("Behavior tree initialized with patrol and learning support")

    def _build_tree(self) -> py_trees.behaviour.Behaviour:
        """
        Build the behavior tree structure with patrol cycle

        Returns:
            Root node of behavior tree
        """
        # Root sequence
        root = py_trees.composites.Sequence(
            name="PooperScooper Main Sequence",
            memory=True
        )

        # Safety check (runs first, always)
        safety_check = SafetyCheckBehavior(
            name="Safety Check",
            safety_system=self.safety
        )

        # Wait for web command to start patrol
        wait_for_command = WaitForPatrolCommandBehavior(
            name="Wait for Patrol Command",
            blackboard=self.blackboard
        )

        # Main patrol cycle
        patrol_cycle = PatrolCycleBehavior(
            name="Patrol Cycle",
            excavator=self.excavator,
            camera=self.camera,
            detector=self.detector,
            flag_detector=self.flag_detector,
            audio_monitor=self.audio_monitor,
            nav_sm=self.nav_sm,
            arm_sm=self.arm_sm,
            patrol_planner=self.patrol_planner,
            position_tracker=self.position_tracker,
            database=self.database,
            optimizer=self.optimizer,
            map_manager=self.map_manager,
            blackboard=self.blackboard
        )

        # Return to home after patrol
        return_home = ReturnHomeBehavior(
            name="Return to Home",
            excavator=self.excavator,
            flag_detector=self.flag_detector,
            camera=self.camera,
            nav_sm=self.nav_sm,
            position_tracker=self.position_tracker
        )

        # Add to root
        root.add_children([
            safety_check,
            wait_for_command,
            patrol_cycle,
            return_home,
        ])

        return root

    def tick(self) -> Status:
        """
        Execute one tick of behavior tree

        Returns:
            Status of tree execution
        """
        # Heartbeat for safety watchdog
        self.safety.heartbeat()

        # Tick the tree
        status = self.root.tick_once()

        return status

    def run(self, max_iterations: int = 1000):
        """
        Run behavior tree loop

        Args:
            max_iterations: Maximum number of iterations
        """
        logger.info("Starting behavior tree execution")

        for i in range(max_iterations):
            status = self.tick()

            if self.safety.emergency_stop:
                logger.error("Emergency stop triggered - halting")
                break

            # Small delay between ticks
            time.sleep(0.1)

            if i % 100 == 0:
                logger.info(f"Iteration {i}, Pickups: {self.blackboard.pickup_count}")

        logger.info(f"Behavior tree execution complete. Total pickups: {self.blackboard.pickup_count}")


# ===== Individual Behavior Implementations =====

class SafetyCheckBehavior(py_trees.behaviour.Behaviour):
    """Check safety systems before each operation"""

    def __init__(self, name: str, safety_system: Any):
        super().__init__(name)
        self.safety = safety_system

    def update(self) -> Status:
        if self.safety.emergency_stop:
            logger.error("EMERGENCY STOP ACTIVE")
            return Status.FAILURE

        if not self.safety.is_safe():
            logger.warning("Safety check failed")
            return Status.FAILURE

        return Status.SUCCESS


class WaitForPatrolCommandBehavior(py_trees.behaviour.Behaviour):
    """Wait for web interface to command patrol start"""

    def __init__(self, name: str, blackboard: Any):
        super().__init__(name)
        self.blackboard = blackboard

    def update(self) -> Status:
        # Check if patrol command has been issued (via web interface)
        if self.blackboard.patrol_active:
            logger.info("Patrol command received - starting patrol")
            return Status.SUCCESS

        logger.debug("Waiting for patrol command...")
        time.sleep(1.0)
        return Status.RUNNING


class PatrolCycleBehavior(py_trees.behaviour.Behaviour):
    """Complete patrol cycle with waypoint navigation and poop pickup"""

    def __init__(self, name: str, excavator, camera, detector, flag_detector, audio_monitor,
                 nav_sm, arm_sm, patrol_planner, position_tracker, database, optimizer, map_manager, blackboard):
        super().__init__(name)
        self.excavator = excavator
        self.camera = camera
        self.detector = detector
        self.flag_detector = flag_detector
        self.audio_monitor = audio_monitor
        self.nav_sm = nav_sm
        self.arm_sm = arm_sm
        self.patrol_planner = patrol_planner
        self.position_tracker = position_tracker
        self.database = database
        self.optimizer = optimizer
        self.map_manager = map_manager
        self.blackboard = blackboard

        self.waypoints = []
        self.current_waypoint_idx = 0
        self.initialized = False

    def initialise(self):
        """Initialize patrol - generate waypoints"""
        if not self.initialized and self.patrol_planner:
            logger.info("Initializing patrol - generating waypoints")
            self.waypoints = self.patrol_planner.get_patrol_waypoints()
            self.current_waypoint_idx = 0
            self.initialized = True

            # Start patrol session in database
            if self.database:
                self.blackboard.session_id = self.database.start_patrol_session()

            # Transition to PATROLLING state
            self.nav_sm.start_patrol()

    def update(self) -> Status:
        # Check if patrol is still active
        if not self.blackboard.patrol_active:
            logger.info("Patrol deactivated - ending patrol")
            return Status.SUCCESS

        # Check if patrol complete
        if self.patrol_planner and self.patrol_planner.is_complete():
            logger.info("Patrol area coverage complete!")
            self.blackboard.patrol_active = False
            return Status.SUCCESS

        # Get current position
        if self.position_tracker:
            current_pos = self.position_tracker.get_current_position()
        else:
            current_pos = None

        # Navigate to next waypoint
        if self.current_waypoint_idx < len(self.waypoints):
            waypoint = self.waypoints[self.current_waypoint_idx]
            self.blackboard.current_waypoint = waypoint

            # Simple navigation (move forward)
            logger.debug(f"Navigating to waypoint {self.current_waypoint_idx+1}/{len(self.waypoints)}")
            self.excavator.move_forward(0.5)

            # Update position
            if self.position_tracker:
                self.position_tracker.update_forward(0.5)

            # Mark cell as visited
            if self.map_manager and current_pos:
                self.map_manager.mark_visited(current_pos.x, current_pos.y)

            self.current_waypoint_idx += 1

        # Scan for poop at this location
        frame = self.camera.capture_frame()
        if frame is not None:
            detections = self.detector.detect(frame)

            if len(detections) > 0:
                # Poop detected - execute pickup with stall retry
                target = detections[0]
                logger.info(f"Poop detected at waypoint with confidence {target.confidence:.2f}")

                # Transition to approaching target
                self.nav_sm.target_found()

                # Execute pickup with retry
                success = self._pickup_with_retry(target, current_pos)

                # Log to database
                if self.database and current_pos:
                    self.database.log_pickup_attempt(
                        success=success,
                        position=(current_pos.x, current_pos.y),
                        target_confidence=target.confidence,
                        arm_timings=self.excavator.timing,
                        failure_reason=None if success else "stall_or_failed",
                        session_id=self.blackboard.session_id
                    )

                # Mark on map
                if self.map_manager and current_pos:
                    self.map_manager.mark_poop_found(current_pos.x, current_pos.y)

                # Update pickup count
                if success:
                    self.blackboard.pickup_count += 1

                # Navigate to disposal and dump
                if success:
                    self._navigate_and_dump()

                # Return to patrolling
                self.nav_sm.continue_patrol()

        # Continue patrol
        return Status.RUNNING

    def _pickup_with_retry(self, target, position) -> bool:
        """
        Execute pickup with automatic stall retry

        Returns:
            True if pickup successful
        """
        logger.info("Attempting pickup with stall retry support")

        # Apply optimized timings from learning
        if self.optimizer:
            optimized = self.optimizer.optimize_parameters()
            for param, value in optimized.items():
                self.excavator.set_timing(param, value)

        # Try pickup with up to 4 retry strategies
        for attempt in range(4):
            # Position for pickup
            logger.debug("Positioning for pickup")
            time.sleep(0.5)

            # Execute pickup sequence
            try:
                self.excavator.pickup_sequence()

                # Update arm state machine
                self.arm_sm.start_pickup()
                self.arm_sm.lowered()
                self.arm_sm.scooped()
                self.arm_sm.lifted()

                # Check for stall during pickup
                if self.audio_monitor.check_for_stall("arm_motor"):
                    logger.warning(f"Stall detected during pickup (attempt {attempt+1}/4)")

                    # Get retry strategy
                    strategy = self.audio_monitor.handle_stall("arm_motor")

                    # Execute retry
                    self.excavator.execute_retry_strategy(strategy, self.audio_monitor)

                    # Reset stall flag
                    self.audio_monitor.reset_stall_flag()

                    # Reset arm state
                    self.arm_sm.abort()

                    # Check if we should skip
                    from hardware.audio_monitor import StallRetryStrategy
                    if strategy == StallRetryStrategy.SKIP:
                        logger.warning("Max retries reached - skipping target")
                        return False

                    # Continue to next retry attempt
                    continue

                else:
                    # No stall - success!
                    self.arm_sm.pickup_verified()
                    logger.info(f"Pickup successful on attempt {attempt+1}")
                    return True

            except Exception as e:
                logger.error(f"Pickup failed with exception: {e}")
                self.arm_sm.abort()
                return False

        # All retries exhausted
        logger.warning("Pickup failed after all retry attempts")
        return False

    def _navigate_and_dump(self):
        """Navigate to disposal flag and dump"""
        logger.info("Navigating to disposal location")

        # Transition to carrying state
        self.arm_sm.arrived_at_dump()

        # Navigate to flag
        max_attempts = 20
        for attempt in range(max_attempts):
            frame = self.camera.capture_frame()
            if frame is None:
                continue

            flag_pos = self.flag_detector.detect_flag(frame)

            if flag_pos is None:
                # Turn to search for flag
                self.excavator.turn_right(0.3)
                continue

            # Navigate toward flag
            direction = self.flag_detector.get_direction_to_flag(flag_pos, frame.shape[:2])

            if direction == "left":
                self.excavator.turn_left(0.3)
            elif direction == "right":
                self.excavator.turn_right(0.3)
            elif direction == "centered":
                self.excavator.move_forward(0.5)

                # Check if close enough
                distance = self.flag_detector.estimate_distance(flag_pos, frame.shape[:2])
                if distance <= 0.7:
                    logger.info("Arrived at disposal location")
                    break

        # Execute dump
        logger.info("Dumping waste")
        self.excavator.dump_sequence()
        self.arm_sm.dumped()


class ReturnHomeBehavior(py_trees.behaviour.Behaviour):
    """Navigate back to home position after patrol"""

    def __init__(self, name: str, excavator, flag_detector, camera, nav_sm, position_tracker):
        super().__init__(name)
        self.excavator = excavator
        self.flag_detector = flag_detector
        self.camera = camera
        self.nav_sm = nav_sm
        self.position_tracker = position_tracker

    def update(self) -> Status:
        logger.info("Returning to home position")

        # Transition to returning state
        self.nav_sm.patrol_complete()

        # Navigate home (simplified - just use flag as home marker for now)
        if self.position_tracker:
            distance = self.position_tracker.distance_to_home()
            logger.info(f"Distance to home: {distance:.2f}m")

            if distance < 0.5:
                logger.info("Arrived at home position")
                self.nav_sm.arrived_at_base()
                return Status.SUCCESS

        # Move toward home (simplified navigation)
        self.excavator.move_backward(1.0)

        if self.position_tracker:
            self.position_tracker.update_backward(1.0)

        return Status.SUCCESS


if __name__ == "__main__":
    """Test behavior tree structure"""
    logger.info("Behavior tree module loaded")
