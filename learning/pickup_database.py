"""
Pickup Database - SQLite database for storing pickup attempts and learning
Records all pickup attempts with success/failure for machine learning
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from loguru import logger


class PickupDatabase:
    """
    SQLite database for pickup attempt logging and analytics

    Stores detailed information about every pickup attempt for learning
    """

    def __init__(self, db_path: str = "data/pooperscooper.db"):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Access columns by name

        # Create tables
        self._create_tables()

        logger.info(f"Pickup database initialized: {db_path}")

    def _create_tables(self) -> None:
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()

        # Pickup attempts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pickup_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                position_x REAL,
                position_y REAL,
                target_confidence REAL,
                target_size INTEGER,
                boom_up_time REAL,
                boom_down_time REAL,
                arm_up_time REAL,
                arm_down_time REAL,
                bucket_scoop_time REAL,
                success INTEGER NOT NULL,
                failure_reason TEXT,
                patrol_session_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Patrol sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patrol_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time REAL NOT NULL,
                end_time REAL,
                coverage_percent REAL,
                total_pickups INTEGER DEFAULT 0,
                successful_pickups INTEGER DEFAULT 0,
                pattern_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Learned parameters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_parameters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parameter_name TEXT NOT NULL UNIQUE,
                parameter_value REAL NOT NULL,
                success_rate REAL,
                attempts_count INTEGER,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Hotspot locations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hotspot_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grid_row INTEGER NOT NULL,
                grid_col INTEGER NOT NULL,
                poop_count INTEGER DEFAULT 1,
                last_found TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(grid_row, grid_col)
            )
        ''')

        self.conn.commit()

        logger.debug("Database tables created/verified")

    def log_pickup_attempt(
        self,
        success: bool,
        position: Optional[Tuple[float, float]] = None,
        target_confidence: Optional[float] = None,
        target_size: Optional[int] = None,
        arm_timings: Optional[Dict[str, float]] = None,
        failure_reason: Optional[str] = None,
        session_id: Optional[int] = None
    ) -> int:
        """
        Log a pickup attempt

        Args:
            success: Whether pickup was successful
            position: (x, y) position of attempt
            target_confidence: Detection confidence score
            target_size: Size of detected target (pixels)
            arm_timings: Dictionary of arm timing parameters
            failure_reason: Reason for failure if unsuccessful
            session_id: Patrol session ID

        Returns:
            Attempt ID
        """
        cursor = self.conn.cursor()

        pos_x, pos_y = position if position else (None, None)

        # Extract arm timings
        if arm_timings:
            boom_up = arm_timings.get('boom_up', None)
            boom_down = arm_timings.get('boom_down', None)
            arm_up = arm_timings.get('arm_up', None)
            arm_down = arm_timings.get('arm_down', None)
            bucket_scoop = arm_timings.get('bucket_scoop', None)
        else:
            boom_up = boom_down = arm_up = arm_down = bucket_scoop = None

        cursor.execute('''
            INSERT INTO pickup_attempts (
                timestamp, position_x, position_y, target_confidence, target_size,
                boom_up_time, boom_down_time, arm_up_time, arm_down_time, bucket_scoop_time,
                success, failure_reason, patrol_session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().timestamp(),
            pos_x, pos_y, target_confidence, target_size,
            boom_up, boom_down, arm_up, arm_down, bucket_scoop,
            1 if success else 0,
            failure_reason,
            session_id
        ))

        self.conn.commit()
        attempt_id = cursor.lastrowid

        logger.info(f"Logged pickup attempt #{attempt_id}: {'SUCCESS' if success else 'FAILURE'}")

        return attempt_id

    def start_patrol_session(self, pattern_type: str) -> int:
        """
        Start a new patrol session

        Args:
            pattern_type: Patrol pattern name

        Returns:
            Session ID
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO patrol_sessions (start_time, pattern_type)
            VALUES (?, ?)
        ''', (datetime.now().timestamp(), pattern_type))

        self.conn.commit()
        session_id = cursor.lastrowid

        logger.info(f"Started patrol session #{session_id}")

        return session_id

    def end_patrol_session(
        self,
        session_id: int,
        coverage_percent: float,
        total_pickups: int,
        successful_pickups: int
    ) -> None:
        """
        End a patrol session

        Args:
            session_id: Session ID
            coverage_percent: Percentage of area covered
            total_pickups: Total pickup attempts
            successful_pickups: Successful pickups
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            UPDATE patrol_sessions
            SET end_time = ?, coverage_percent = ?, total_pickups = ?, successful_pickups = ?
            WHERE id = ?
        ''', (datetime.now().timestamp(), coverage_percent, total_pickups, successful_pickups, session_id))

        self.conn.commit()

        logger.info(f"Ended patrol session #{session_id}: {successful_pickups}/{total_pickups} successful")

    def get_success_rate(self, last_n: Optional[int] = None) -> float:
        """
        Calculate success rate

        Args:
            last_n: Consider only last N attempts (None = all)

        Returns:
            Success rate (0.0 to 1.0)
        """
        cursor = self.conn.cursor()

        if last_n:
            cursor.execute('''
                SELECT AVG(success) FROM (
                    SELECT success FROM pickup_attempts
                    ORDER BY timestamp DESC LIMIT ?
                )
            ''', (last_n,))
        else:
            cursor.execute('SELECT AVG(success) FROM pickup_attempts')

        result = cursor.fetchone()
        return result[0] if result[0] is not None else 0.0

    def get_best_arm_timings(self) -> Dict[str, float]:
        """
        Get arm timings with highest success rate

        Returns:
            Dictionary of optimal timing parameters
        """
        cursor = self.conn.cursor()

        # Get average timings from successful attempts
        cursor.execute('''
            SELECT
                AVG(boom_up_time) as boom_up,
                AVG(boom_down_time) as boom_down,
                AVG(arm_up_time) as arm_up,
                AVG(arm_down_time) as arm_down,
                AVG(bucket_scoop_time) as bucket_scoop
            FROM pickup_attempts
            WHERE success = 1
        ''')

        row = cursor.fetchone()

        if row[0] is None:
            # No successful attempts yet
            return {}

        return {
            'boom_up': row[0],
            'boom_down': row[1],
            'arm_up': row[2],
            'arm_down': row[3],
            'bucket_scoop': row[4]
        }

    def get_failure_modes(self) -> Dict[str, int]:
        """
        Get counts of different failure modes

        Returns:
            Dictionary mapping failure reasons to counts
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT failure_reason, COUNT(*) as count
            FROM pickup_attempts
            WHERE success = 0 AND failure_reason IS NOT NULL
            GROUP BY failure_reason
            ORDER BY count DESC
        ''')

        return {row[0]: row[1] for row in cursor.fetchall()}

    def record_hotspot(self, grid_row: int, grid_col: int) -> None:
        """
        Record poop found at grid location

        Args:
            grid_row: Grid row index
            grid_col: Grid column index
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO hotspot_locations (grid_row, grid_col, poop_count, last_found)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(grid_row, grid_col) DO UPDATE SET
                poop_count = poop_count + 1,
                last_found = CURRENT_TIMESTAMP
        ''', (grid_row, grid_col))

        self.conn.commit()

    def get_hotspots(self, min_count: int = 2) -> List[Tuple[int, int, int]]:
        """
        Get hotspot locations

        Args:
            min_count: Minimum poop count to be considered hotspot

        Returns:
            List of (row, col, count) tuples
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT grid_row, grid_col, poop_count
            FROM hotspot_locations
            WHERE poop_count >= ?
            ORDER BY poop_count DESC
        ''', (min_count,))

        return [(row[0], row[1], row[2]) for row in cursor.fetchall()]

    def save_learned_parameter(self, name: str, value: float, success_rate: float, attempts: int) -> None:
        """
        Save learned parameter

        Args:
            name: Parameter name
            value: Parameter value
            success_rate: Success rate with this parameter
            attempts: Number of attempts
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            INSERT INTO learned_parameters (parameter_name, parameter_value, success_rate, attempts_count)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(parameter_name) DO UPDATE SET
                parameter_value = ?,
                success_rate = ?,
                attempts_count = ?,
                updated_at = CURRENT_TIMESTAMP
        ''', (name, value, success_rate, attempts, value, success_rate, attempts))

        self.conn.commit()

    def get_learned_parameter(self, name: str) -> Optional[float]:
        """
        Get learned parameter value

        Args:
            name: Parameter name

        Returns:
            Parameter value or None
        """
        cursor = self.conn.cursor()

        cursor.execute('''
            SELECT parameter_value FROM learned_parameters
            WHERE parameter_name = ?
        ''', (name,))

        result = cursor.fetchone()
        return result[0] if result else None

    def get_statistics(self) -> Dict:
        """
        Get overall statistics

        Returns:
            Dictionary with statistics
        """
        cursor = self.conn.cursor()

        # Total attempts
        cursor.execute('SELECT COUNT(*) FROM pickup_attempts')
        total_attempts = cursor.fetchone()[0]

        # Successful attempts
        cursor.execute('SELECT COUNT(*) FROM pickup_attempts WHERE success = 1')
        successful_attempts = cursor.fetchone()[0]

        # Success rate
        success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0.0

        # Total sessions
        cursor.execute('SELECT COUNT(*) FROM patrol_sessions')
        total_sessions = cursor.fetchone()[0]

        return {
            'total_attempts': total_attempts,
            'successful_attempts': successful_attempts,
            'failed_attempts': total_attempts - successful_attempts,
            'success_rate': success_rate,
            'total_sessions': total_sessions,
        }

    def close(self) -> None:
        """Close database connection"""
        self.conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    """Test pickup database"""

    db = PickupDatabase("test_pooperscooper.db")

    logger.info("Testing database...")

    # Start session
    session_id = db.start_patrol_session("lawnmower")

    # Log some attempts
    for i in range(10):
        success = i % 3 != 0  # 2/3 success rate
        db.log_pickup_attempt(
            success=success,
            position=(i * 0.5, i * 0.3),
            target_confidence=0.85,
            target_size=500,
            arm_timings={'boom_up': 2.0, 'boom_down': 2.0, 'arm_down': 1.5, 'bucket_scoop': 1.0},
            failure_reason="dropped" if not success else None,
            session_id=session_id
        )

    # End session
    db.end_patrol_session(session_id, 95.0, 10, 7)

    # Get statistics
    stats = db.get_statistics()
    logger.info(f"Statistics: {stats}")

    success_rate = db.get_success_rate(last_n=5)
    logger.info(f"Success rate (last 5): {success_rate:.2%}")

    best_timings = db.get_best_arm_timings()
    logger.info(f"Best arm timings: {best_timings}")

    db.close()
    logger.info("Test complete")
