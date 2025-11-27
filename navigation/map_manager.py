"""
Map Manager - Occupancy grid and hotspot tracking
Manages 2D map of patrol area with visited locations and poop hotspots
"""

import numpy as np
from typing import List, Tuple
from loguru import logger


class MapManager:
    """
    Manages 2D occupancy grid and hotspot locations

    Tracks visited areas and identifies frequently soiled locations
    """

    def __init__(self, config: dict, database):
        """
        Initialize map manager

        Args:
            config: Configuration dictionary
            database: PickupDatabase instance
        """
        self.config = config
        self.database = database

        # Map parameters
        self.area_x = config['patrol']['area']['x']
        self.area_y = config['patrol']['area']['y']
        self.area_width = config['patrol']['area']['width']
        self.area_height = config['patrol']['area']['height']
        self.cell_size = config['patrol']['grid_cell_size']

        # Calculate grid dimensions
        self.grid_cols = int(np.ceil(self.area_width / self.cell_size))
        self.grid_rows = int(np.ceil(self.area_height / self.cell_size))

        # Occupancy grid (0=unvisited, 1=visited)
        self.occupancy_grid = np.zeros((self.grid_rows, self.grid_cols), dtype=int)

        # Hotspot map (counts of poops found per cell)
        self.hotspot_map = np.zeros((self.grid_rows, self.grid_cols), dtype=int)

        logger.info(f"Map manager initialized: {self.grid_rows}x{self.grid_cols} grid")

        # Load hotspots from database
        self._load_hotspots()

    def _load_hotspots(self) -> None:
        """Load hotspot data from database"""
        hotspots = self.database.get_hotspots(min_count=1)

        for row, col, count in hotspots:
            if 0 <= row < self.grid_rows and 0 <= col < self.grid_cols:
                self.hotspot_map[row, col] = count

        logger.info(f"Loaded {len(hotspots)} hotspots from database")

    def position_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """
        Convert world position to grid coordinates

        Args:
            x, y: World coordinates (meters)

        Returns:
            (row, col) grid coordinates
        """
        col = int((x - self.area_x) / self.cell_size)
        row = int((y - self.area_y) / self.cell_size)

        # Clamp to grid bounds
        col = max(0, min(col, self.grid_cols - 1))
        row = max(0, min(row, self.grid_rows - 1))

        return (row, col)

    def grid_to_position(self, row: int, col: int) -> Tuple[float, float]:
        """
        Convert grid coordinates to world position (center of cell)

        Args:
            row, col: Grid coordinates

        Returns:
            (x, y) world coordinates
        """
        x = self.area_x + (col + 0.5) * self.cell_size
        y = self.area_y + (row + 0.5) * self.cell_size

        return (x, y)

    def mark_visited(self, x: float, y: float) -> None:
        """Mark position as visited"""
        row, col = self.position_to_grid(x, y)
        self.occupancy_grid[row, col] = 1

    def mark_poop_found(self, x: float, y: float) -> None:
        """
        Mark poop found at position

        Args:
            x, y: Position where poop was found
        """
        row, col = self.position_to_grid(x, y)
        self.hotspot_map[row, col] += 1

        # Save to database
        self.database.record_hotspot(row, col)

        logger.info(f"Poop found at grid ({row}, {col}), count now: {self.hotspot_map[row, col]}")

    def get_hotspots(self, min_count: int = 2) -> List[Tuple[int, int]]:
        """
        Get hotspot locations

        Args:
            min_count: Minimum count to be considered hotspot

        Returns:
            List of (row, col) tuples
        """
        hotspots = []
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                if self.hotspot_map[row, col] >= min_count:
                    hotspots.append((row, col))

        return hotspots

    def get_coverage_percentage(self) -> float:
        """Calculate percentage of area visited"""
        visited = np.sum(self.occupancy_grid == 1)
        total = self.grid_rows * self.grid_cols
        return (visited / total) * 100

    def reset_occupancy(self) -> None:
        """Reset occupancy grid (for new patrol)"""
        self.occupancy_grid.fill(0)

    def get_map_data(self) -> dict:
        """
        Get map data for visualization

        Returns:
            Dictionary with map arrays
        """
        return {
            'occupancy': self.occupancy_grid.tolist(),
            'hotspots': self.hotspot_map.tolist(),
            'grid_rows': self.grid_rows,
            'grid_cols': self.grid_cols,
            'cell_size': self.cell_size,
        }


if __name__ == "__main__":
    """Test map manager"""
    import yaml
    from learning.pickup_database import PickupDatabase

    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    db = PickupDatabase("test_pooperscooper.db")
    map_mgr = MapManager(config, db)

    logger.info("Testing map manager...")

    # Mark some positions visited
    map_mgr.mark_visited(1.0, 1.0)
    map_mgr.mark_visited(2.0, 2.0)

    # Mark poops found
    map_mgr.mark_poop_found(3.0, 3.0)
    map_mgr.mark_poop_found(3.0, 3.0)  # Same location twice

    hotspots = map_mgr.get_hotspots(min_count=2)
    logger.info(f"Hotspots: {hotspots}")

    coverage = map_mgr.get_coverage_percentage()
    logger.info(f"Coverage: {coverage:.1f}%")

    db.close()
    logger.info("Test complete")
