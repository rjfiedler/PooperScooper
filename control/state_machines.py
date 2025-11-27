"""
State Machines for Navigation and Manipulation
Manages excavator states and transitions
"""

from enum import Enum
from loguru import logger
from transitions import Machine


class NavigationState(Enum):
    """Navigation states"""
    IDLE = "idle"
    PATROLLING = "patrolling"
    SEARCHING = "searching"
    APPROACHING_TARGET = "approaching_target"
    POSITIONING = "positioning"
    RETURNING_TO_BASE = "returning_to_base"
    ARRIVED = "arrived"


class ManipulationState(Enum):
    """Arm manipulation states"""
    HOME = "home"
    LOWERING = "lowering"
    SCOOPING = "scooping"
    LIFTING = "lifting"
    CARRYING = "carrying"
    DUMPING = "dumping"
    VERIFYING = "verifying"


class NavigationStateMachine:
    """
    State machine for excavator navigation

    Manages movement between locations and target tracking
    """

    states = [state.value for state in NavigationState]

    transitions = [
        # From IDLE
        {'trigger': 'start_patrol', 'source': 'idle', 'dest': 'patrolling'},
        {'trigger': 'start_search', 'source': 'idle', 'dest': 'searching'},

        # From PATROLLING
        {'trigger': 'target_found', 'source': 'patrolling', 'dest': 'approaching_target'},
        {'trigger': 'patrol_complete', 'source': 'patrolling', 'dest': 'returning_to_base'},
        {'trigger': 'continue_patrol', 'source': 'patrolling', 'dest': 'patrolling'},

        # From SEARCHING
        {'trigger': 'target_found', 'source': 'searching', 'dest': 'approaching_target'},
        {'trigger': 'return_home', 'source': 'searching', 'dest': 'returning_to_base'},

        # From APPROACHING_TARGET
        {'trigger': 'arrived_at_target', 'source': 'approaching_target', 'dest': 'positioning'},
        {'trigger': 'lost_target', 'source': 'approaching_target', 'dest': 'patrolling'},

        # From POSITIONING
        {'trigger': 'positioned', 'source': 'positioning', 'dest': 'arrived'},
        {'trigger': 'repositioning_needed', 'source': 'positioning', 'dest': 'approaching_target'},

        # From ARRIVED
        {'trigger': 'pickup_complete', 'source': 'arrived', 'dest': 'patrolling'},
        {'trigger': 'pickup_failed', 'source': 'arrived', 'dest': 'patrolling'},

        # From RETURNING_TO_BASE
        {'trigger': 'arrived_at_base', 'source': 'returning_to_base', 'dest': 'idle'},

        # Emergency transitions
        {'trigger': 'reset', 'source': '*', 'dest': 'idle'},
    ]

    def __init__(self):
        """Initialize navigation state machine"""
        self.machine = Machine(
            model=self,
            states=NavigationStateMachine.states,
            transitions=NavigationStateMachine.transitions,
            initial='idle',
            auto_transitions=False
        )

        logger.info("Navigation state machine initialized")

    def on_enter_patrolling(self):
        """Callback when entering PATROLLING state"""
        logger.info("[NAV] Entering PATROLLING state")

    def on_enter_searching(self):
        """Callback when entering SEARCHING state"""
        logger.info("[NAV] Entering SEARCHING state")

    def on_enter_approaching_target(self):
        """Callback when entering APPROACHING_TARGET state"""
        logger.info("[NAV] Entering APPROACHING_TARGET state")

    def on_enter_positioning(self):
        """Callback when entering POSITIONING state"""
        logger.info("[NAV] Entering POSITIONING state")

    def on_enter_arrived(self):
        """Callback when entering ARRIVED state"""
        logger.info("[NAV] Entering ARRIVED state")

    def on_enter_returning_to_base(self):
        """Callback when entering RETURNING_TO_BASE state"""
        logger.info("[NAV] Entering RETURNING_TO_BASE state")


class ManipulationStateMachine:
    """
    State machine for excavator arm manipulation

    Manages arm movements for picking and dumping
    """

    states = [state.value for state in ManipulationState]

    transitions = [
        # Pickup sequence
        {'trigger': 'start_pickup', 'source': 'home', 'dest': 'lowering'},
        {'trigger': 'lowered', 'source': 'lowering', 'dest': 'scooping'},
        {'trigger': 'scooped', 'source': 'scooping', 'dest': 'lifting'},
        {'trigger': 'lifted', 'source': 'lifting', 'dest': 'verifying'},

        # Verification
        {'trigger': 'pickup_verified', 'source': 'verifying', 'dest': 'carrying'},
        {'trigger': 'pickup_failed_verify', 'source': 'verifying', 'dest': 'lowering'},

        # Transport
        {'trigger': 'arrived_at_dump', 'source': 'carrying', 'dest': 'dumping'},

        # Dump sequence
        {'trigger': 'dumped', 'source': 'dumping', 'dest': 'home'},

        # Emergency/reset
        {'trigger': 'reset', 'source': '*', 'dest': 'home'},
        {'trigger': 'abort', 'source': '*', 'dest': 'home'},
    ]

    def __init__(self):
        """Initialize manipulation state machine"""
        self.machine = Machine(
            model=self,
            states=ManipulationStateMachine.states,
            transitions=ManipulationStateMachine.transitions,
            initial='home',
            auto_transitions=False
        )

        logger.info("Manipulation state machine initialized")

    def on_enter_lowering(self):
        """Callback when entering LOWERING state"""
        logger.info("[ARM] Entering LOWERING state")

    def on_enter_scooping(self):
        """Callback when entering SCOOPING state"""
        logger.info("[ARM] Entering SCOOPING state")

    def on_enter_lifting(self):
        """Callback when entering LIFTING state"""
        logger.info("[ARM] Entering LIFTING state")

    def on_enter_verifying(self):
        """Callback when entering VERIFYING state"""
        logger.info("[ARM] Entering VERIFYING state")

    def on_enter_carrying(self):
        """Callback when entering CARRYING state"""
        logger.info("[ARM] Entering CARRYING state")

    def on_enter_dumping(self):
        """Callback when entering DUMPING state"""
        logger.info("[ARM] Entering DUMPING state")

    def on_enter_home(self):
        """Callback when entering HOME state"""
        logger.info("[ARM] Entering HOME state")


if __name__ == "__main__":
    """Test state machines"""

    # Test navigation state machine
    nav = NavigationStateMachine()
    logger.info(f"Initial state: {nav.state}")

    nav.start_search()
    logger.info(f"After start_search: {nav.state}")

    nav.target_found()
    logger.info(f"After target_found: {nav.state}")

    nav.arrived_at_target()
    logger.info(f"After arrived_at_target: {nav.state}")

    # Test manipulation state machine
    arm = ManipulationStateMachine()
    logger.info(f"Initial arm state: {arm.state}")

    arm.start_pickup()
    logger.info(f"After start_pickup: {arm.state}")

    arm.lowered()
    logger.info(f"After lowered: {arm.state}")

    arm.scooped()
    logger.info(f"After scooped: {arm.state}")

    logger.info("State machine test complete")
