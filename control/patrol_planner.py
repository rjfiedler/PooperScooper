"""
Patrol Planner - Systematic area coverage with multiple patterns
Generates movement sequences for complete yard coverage
"""

import numpy as np
import time
from typing import List, Tuple, Optional
from enum import Enum
from loguru import logger


class PatternType(Enum):
    """Patrol pattern types"""
    LAWNMOWER = "lawnmower"
    SPIRAL = "spiral"
    GRID = "grid"


class CellStatus(Enum):
    """Grid cell status"""
    UNVISITED = 0
    VISITED = 1
    OBSTACLE = 2


class PatrolPlanner:
    """
    Plans systematic patrol patterns for area coverage

    Creates waypoint sequences and tracks coverage progress
    """

    def __init__(self, config: dict):
        """
        Initialize patrol planner

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Patrol area (meters)
        self.area_x = config['patrol']['area']['x']
        self.area_y = config['patrol']['area']['y']
        self.area_width = config['patrol']['area']['width']
        self.area_height = config['patrol']['area']['height']

        # Grid configuration
        self.cell_size = config['patrol']['grid_cell_size']
        self.overlap_percent = config['patrol']['overlap_percent']

        # Pattern type
        pattern_name = config['patrol']['pattern']
        self.pattern = PatternType(pattern_name)

        # Calculate grid dimensions
        self.grid_cols = int(np.ceil(self.area_width / self.cell_size))
        self.grid_rows = int(np.ceil(self.area_height / self.cell_size))

        # Coverage grid
        self.coverage_grid = np.zeros((self.grid_rows, self.grid_cols), dtype=int)

        # Waypoints queue
        self.waypoints: List[Tuple[float, float]] = []
        self.current_waypoint_index = 0

        # Statistics
        self.start_time = None
        self.total_cells = self.grid_rows * self.grid_cols

        logger.info(f"Patrol planner initialized:")
        logger.info(f"  Area: {self.area_width}x{self.area_height}m at ({self.area_x}, {self.area_y})")
        logger.info(f"  Grid: {self.grid_rows}x{self.grid_cols} cells ({self.cell_size}m each)")
        logger.info(f"  Pattern: {self.pattern.value}")

    def generate_patrol_path(self) -> None:
        """Generate waypoints for selected pattern"""
        if self.pattern == PatternType.LAWNMOWER:
            self._generate_lawnmower()
        elif self.pattern == PatternType.SPIRAL:
            self._generate_spiral()
        elif self.pattern == PatternType.GRID:
            self._generate_grid()

        logger.info(f"Generated {len(self.waypoints)} waypoints for patrol")

    def _generate_lawnmower(self) -> None:
        """Generate lawnmower (boustrophedon) pattern"""
        self.waypoints = []

        # Calculate effective cell size with overlap
        effective_size = self.cell_size * (1 - self.overlap_percent / 100)

        # Sweep left-to-right, then move up, sweep right-to-left
        for row in range(self.grid_rows):
            y = self.area_y + (row + 0.5) * effective_size

            if row % 2 == 0:
                # Even rows: left to right
                for col in range(self.grid_cols):
                    x = self.area_x + (col + 0.5) * effective_size
                    self.waypoints.append((x, y))
            else:
                # Odd rows: right to left
                for col in range(self.grid_cols - 1, -1, -1):
                    x = self.area_x + (col + 0.5) * effective_size
                    self.waypoints.append((x, y))

    def _generate_spiral(self) -> None:
        """Generate spiral pattern from outside to center"""
        self.waypoints = []

        # Start from corners and spiral inward
        min_row, max_row = 0, self.grid_rows - 1
        min_col, max_col = 0, self.grid_cols - 1

        while min_row <= max_row and min_col <= max_col:
            # Top row
            for col in range(min_col, max_col + 1):
                x = self.area_x + (col + 0.5) * self.cell_size
                y = self.area_y + (min_row + 0.5) * self.cell_size
                self.waypoints.append((x, y))
            min_row += 1

            # Right column
            for row in range(min_row, max_row + 1):
                x = self.area_x + (max_col + 0.5) * self.cell_size
                y = self.area_y + (row + 0.5) * self.cell_size
                self.waypoints.append((x, y))
            max_col -= 1

            if min_row <= max_row:
                # Bottom row
                for col in range(max_col, min_col - 1, -1):
                    x = self.area_x + (col + 0.5) * self.cell_size
                    y = self.area_y + (max_row + 0.5) * self.cell_size
                    self.waypoints.append((x, y))
                max_row -= 1

            if min_col <= max_col:
                # Left column
                for row in range(max_row, min_row - 1, -1):
                    x = self.area_x + (min_col + 0.5) * self.cell_size
                    y = self.area_y + (row + 0.5) * self.cell_size
                    self.waypoints.append((x, y))
                min_col += 1

    def _generate_grid(self) -> None:
        """Generate simple grid pattern (row by row)"""
        self.waypoints = []

        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                x = self.area_x + (col + 0.5) * self.cell_size
                y = self.area_y + (row + 0.5) * self.cell_size
                self.waypoints.append((x, y))

    def mark_visited(self, x: float, y: float) -> None:
        """
        Mark grid cell as visited

        Args:
            x, y: Position coordinates (meters)
        """
        # Convert to grid coordinates
        col = int((x - self.area_x) / self.cell_size)
        row = int((y - self.area_y) / self.cell_size)

        # Bounds check
        if 0 <= row < self.grid_rows and 0 <= col < self.grid_cols:
            self.coverage_grid[row, col] = CellStatus.VISITED.value

    def get_coverage_percentage(self) -> float:
        """
        Calculate percentage of area covered

        Returns:
            Coverage percentage (0-100)
        """
        visited_cells = np.sum(self.coverage_grid == CellStatus.VISITED.value)
        return (visited_cells / self.total_cells) * 100

    def get_next_waypoint(self) -> Optional[Tuple[float, float]]:
        """
        Get next waypoint in patrol path

        Returns:
            (x, y) coordinates or None if path complete
        """
        if self.current_waypoint_index < len(self.waypoints):
            waypoint = self.waypoints[self.current_waypoint_index]
            self.current_waypoint_index += 1
            return waypoint

        return None

    def has_more_waypoints(self) -> bool:
        """Check if there are more waypoints to visit"""
        return self.current_waypoint_index < len(self.waypoints)

    def reset_patrol(self) -> None:
        """Reset patrol state for new patrol session"""
        self.coverage_grid.fill(0)
        self.current_waypoint_index = 0
        self.start_time = time.time()
        logger.info("Patrol reset - starting new session")

    def get_coverage_grid(self) -> np.ndarray:
        """
        Get coverage grid for visualization

        Returns:
            2D numpy array with cell statuses
        """
        return self.coverage_grid.copy()

    def get_unvisited_cells(self) -> List[Tuple[int, int]]:
        """
        Get list of unvisited grid cells

        Returns:
            List of (row, col) tuples
        """
        unvisited = []
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                if self.coverage_grid[row, col] == CellStatus.UNVISITED.value:
                    unvisited.append((row, col))
        return unvisited

    def is_patrol_complete(self, threshold: float = 95.0) -> bool:
        """
        Check if patrol is complete

        Args:
            threshold: Coverage percentage to consider complete (default 95%)

        Returns:
            True if coverage exceeds threshold
        """
        coverage = self.get_coverage_percentage()
        return coverage >= threshold

    def get_patrol_statistics(self) -> dict:
        """
        Get patrol statistics

        Returns:
            Dictionary with statistics
        """
        elapsed_time = time.time() - self.start_time if self.start_time else 0

        return {
            'coverage_percent': self.get_coverage_percentage(),
            'visited_cells': np.sum(self.coverage_grid == CellStatus.VISITED.value),
            'total_cells': self.total_cells,
            'waypoints_completed': self.current_waypoint_index,
            'total_waypoints': len(self.waypoints),
            'elapsed_time': elapsed_time,
            'pattern': self.pattern.value,
        }

    def save_coverage_map(self, filepath: str) -> None:
        """
        Save coverage grid to file

        Args:
            filepath: Path to save file
        """
        np.save(filepath, self.coverage_grid)
        logger.info(f"Coverage map saved to {filepath}")

    def load_coverage_map(self, filepath: str) -> None:
        """
        Load coverage grid from file

        Args:
            filepath: Path to load from
        """
        self.coverage_grid = np.load(filepath)
        logger.info(f"Coverage map loaded from {filepath}")


if __name__ == "__main__":
    """Test patrol planner"""
    import yaml

    # Load config
    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    planner = PatrolPlanner(config)

    logger.info("Generating patrol path...")
    planner.generate_patrol_path()

    logger.info(f"Total waypoints: {len(planner.waypoints)}")

    # Simulate visiting waypoints
    planner.reset_patrol()

    for i in range(min(10, len(planner.waypoints))):
        waypoint = planner.get_next_waypoint()
        if waypoint:
            logger.info(f"Waypoint {i+1}: ({waypoint[0]:.2f}, {waypoint[1]:.2f})")
            planner.mark_visited(waypoint[0], waypoint[1])

    stats = planner.get_patrol_statistics()
    logger.info(f"Statistics: {stats}")

    logger.info("Test complete")
