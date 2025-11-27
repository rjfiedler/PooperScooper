"""
Path Planner - A* path planning for navigation
Finds optimal paths avoiding obstacles and planning efficient routes
"""

import numpy as np
import heapq
from typing import List, Tuple, Optional
from loguru import logger


class PathPlanner:
    """
    A* path planning for excavator navigation

    Plans efficient paths between waypoints
    """

    def __init__(self, map_manager):
        """
        Initialize path planner

        Args:
            map_manager: MapManager instance
        """
        self.map_manager = map_manager

    def plan_path(
        self,
        start: Tuple[float, float],
        goal: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """
        Plan path from start to goal using A*

        Args:
            start: (x, y) start position
            goal: (x, y) goal position

        Returns:
            List of (x, y) waypoints
        """
        # Convert to grid coordinates
        start_grid = self.map_manager.position_to_grid(start[0], start[1])
        goal_grid = self.map_manager.position_to_grid(goal[0], goal[1])

        # Run A*
        path_grid = self._astar(start_grid, goal_grid)

        if not path_grid:
            logger.warning(f"No path found from {start} to {goal}")
            return []

        # Convert back to world coordinates
        path_world = [
            self.map_manager.grid_to_position(row, col)
            for row, col in path_grid
        ]

        logger.info(f"Planned path with {len(path_world)} waypoints")

        return path_world

    def _astar(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """
        A* pathfinding algorithm

        Args:
            start: (row, col) start cell
            goal: (row, col) goal cell

        Returns:
            List of (row, col) cells
        """
        def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
            """Manhattan distance heuristic"""
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def get_neighbors(cell: Tuple[int, int]) -> List[Tuple[int, int]]:
            """Get valid neighboring cells"""
            row, col = cell
            neighbors = []

            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:  # 4-connected
                new_row, new_col = row + dr, col + dc

                if (0 <= new_row < self.map_manager.grid_rows and
                    0 <= new_col < self.map_manager.grid_cols):
                    neighbors.append((new_row, new_col))

            return neighbors

        # Priority queue: (f_score, counter, cell)
        open_set = []
        counter = 0
        heapq.heappush(open_set, (0, counter, start))

        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}

        while open_set:
            _, _, current = heapq.heappop(open_set)

            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                path.reverse()
                return path

            for neighbor in get_neighbors(current):
                tentative_g = g_score[current] + 1

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + heuristic(neighbor, goal)
                    f_score[neighbor] = f

                    counter += 1
                    heapq.heappush(open_set, (f, counter, neighbor))

        return []  # No path found

    def plan_path_to_home(
        self,
        current_position: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """
        Plan path from current position to home

        Args:
            current_position: (x, y) current position

        Returns:
            List of waypoints to home
        """
        home_x = self.map_manager.config['patrol']['home_position']['x']
        home_y = self.map_manager.config['patrol']['home_position']['y']

        return self.plan_path(current_position, (home_x, home_y))


if __name__ == "__main__":
    """Test path planner"""
    import yaml
    from learning.pickup_database import PickupDatabase
    from map_manager import MapManager

    with open("../config.yaml", "r") as f:
        config = yaml.safe_load(f)

    db = PickupDatabase("test_pooperscooper.db")
    map_mgr = MapManager(config, db)
    planner = PathPlanner(map_mgr)

    logger.info("Testing path planner...")

    # Plan a path
    path = planner.plan_path((1.0, 1.0), (5.0, 5.0))
    logger.info(f"Path length: {len(path)} waypoints")

    # Plan path to home
    home_path = planner.plan_path_to_home((8.0, 8.0))
    logger.info(f"Path to home: {len(home_path)} waypoints")

    db.close()
    logger.info("Test complete")
