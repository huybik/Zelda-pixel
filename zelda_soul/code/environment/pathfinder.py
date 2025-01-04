import pygame
from queue import PriorityQueue
import random
from typing import TYPE_CHECKING, List, Optional, TypeAlias, Tuple, Union

if TYPE_CHECKING:
    from entities.creature import Creature
    from entities.resource import Resource
    from environment.env import Environment

Location: TypeAlias = Tuple[int, int]


class Pathfinder:
    def __init__(self):
        pass

    def get_all_movable_cells(
        self, creature: "Creature", env: "Environment"
    ) -> List[Location]:
        movable_cells = []
        x, y = creature.location
        move_range = creature.stats.move_speed

        for dy in range(-move_range, move_range + 1):
            for dx in range(-move_range, move_range + 1):
                new_x = x + dx
                new_y = y + dy

                if 0 <= new_x < env.config.size and 0 <= new_y < env.config.size:
                    distance = abs(dx) + abs(dy)
                    if distance <= move_range and env.grid[new_y][new_x] == "-1":
                        movable_cells.append((new_x, new_y))

        return movable_cells

    def get_all_entities_in_range(
        self, creature: "Creature", env: "Environment"
    ) -> List[str]:
        """Get all entity IDs within move range of the creature."""
        x, y = creature.location
        move_range = creature.stats.move_speed
        entities_in_range = []

        for dy in range(-move_range, move_range + 1):
            for dx in range(-move_range, move_range + 1):
                new_x = x + dx
                new_y = y + dy

                if 0 <= new_x < env.config.size and 0 <= new_y < env.config.size:
                    entity_id = env.grid[new_y][new_x]
                    if entity_id != "-1":
                        entities_in_range.append(entity_id)

        return entities_in_range

    def to_grid(pos, tile_size):
        return (int(pos.x // tile_size), int(pos.y // tile_size))

    def to_world(grid, tile_size):
        return pygame.math.Vector2(
            grid[0] * tile_size + tile_size / 2,
            grid[1] * tile_size + tile_size / 2,
        )

    def astar_pathfinding(self, start, goal, obstacles, tile_size):

        def find_nearest_walkable(grid, obstacle_grids):
            # Check all 4-connected neighbors
            neighbors = [
                (grid[0] + dx, grid[1] + dy)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
            ]
            # Return the first valid neighbor that is not an obstacle
            for neighbor in neighbors:
                if neighbor not in obstacle_grids:
                    return neighbor
            return None  # No valid adjacent grid

        def get_occupied_grids(rect, tile_size):
            """Returns all grid positions occupied by a rectangular obstacle."""
            grids = set()
            start_x = int(rect.left // tile_size)
            start_y = int(rect.top // tile_size)
            end_x = int(rect.right // tile_size)
            end_y = int(rect.bottom // tile_size)

            for x in range(start_x, end_x + 1):
                for y in range(start_y, end_y + 1):
                    grids.add((x, y))
            return grids

        start_grid = self.to_grid(start, tile_size)
        goal_grid = self.to_grid(goal, tile_size)

        # Mark all occupied grids
        obstacle_grids = set()
        for obj in obstacles:
            obstacle_grids.update(get_occupied_grids(obj, tile_size))

        # Adjust goal if it's in the obstacle grid
        if goal_grid in obstacle_grids:
            goal_grid = find_nearest_walkable(goal_grid, obstacle_grids)
            if not goal_grid:
                return []  # No valid path available

        # Heuristic function (Manhattan distance)
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        # A* setup
        open_set = PriorityQueue()
        open_set.put((0, start_grid))
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: heuristic(start_grid, goal_grid)}

        while not open_set.empty():
            _, current_grid = open_set.get()

            if current_grid == goal_grid:
                # Reconstruct path
                path = []
                while current_grid in came_from:
                    path.append(self.to_world(current_grid, tile_size))
                    current_grid = came_from[current_grid]
                path.reverse()
                return path

            # Explore neighbors
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (current_grid[0] + dx, current_grid[1] + dy)
                if neighbor in obstacle_grids:
                    continue

                tentative_g_score = g_score[current_grid] + 1
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current_grid
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(
                        neighbor, goal_grid
                    )
                    open_set.put((f_score[neighbor], neighbor))

        return []  # No path found

    def get_random_empty_location(self, env: "Environment") -> Optional[Location]:
        """Get a random empty cell in the grid."""
        empty_cells = []
        for y in range(env.config.size):
            for x in range(env.config.size):
                if env.grid[y][x] == "-1":
                    empty_cells.append((x, y))

        if empty_cells:
            location = random.choice(empty_cells)
            return location
        return None

    def get_adjacent_entities(self, location: Location) -> List[str]:
        x, y = location
        adjacent_entities = []

        # Check all adjacent cells (including diagonals)
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue

                new_x = x + dx
                new_y = y + dy

                # Check if within bounds
                if 0 <= new_x < self.config.size and 0 <= new_y < self.config.size:
                    entity_id = self.grid[new_y][new_x]
                    if entity_id != "-1":
                        adjacent_entities.append(entity_id)

        return adjacent_entities

    def get_valid_adjacent_cell(
        self, location: Location, env: "Environment", include_diagonals: bool = True
    ) -> List[Location]:

        x, y = location
        valid_cells = []

        # Check all adjacent cells (including diagonals)
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if not include_diagonals and (dx != 0 and dy != 0):
                    continue
                if dx == 0 and dy == 0:
                    continue

                new_x = x + dx
                new_y = y + dy

                # Check if within bounds and empty
                if (
                    0 <= new_x < env.config.size
                    and 0 <= new_y < env.config.size
                    and env.grid[new_y][new_x] == "-1"
                ):
                    valid_cells.append((new_x, new_y))

        return valid_cells

    def relocate(
        self, c: "Creature", new_location: Location, env: "Environment"
    ) -> bool:
        old_x, old_y = c.location
        new_x, new_y = new_location

        # Check if new location is within bounds and empty
        if (
            0 <= new_x < env.config.size
            and 0 <= new_y < env.config.size
            and env.grid[new_y][new_x] == "-1"
        ):

            # Update grid
            env.grid[old_y][old_x] = "-1"
            env.grid[new_y][new_x] = c.id

            # Update entity location
            c.location = new_location
            return True

        return False

    def is_adjacent(self, a: Location, b: Location) -> bool:
        """Check if two locations are adjacent."""
        x1, y1 = a
        x2, y2 = b
        return abs(x1 - x2) <= 1 and abs(y1 - y2) <= 1

    def a_star_path_finder(
        self, start: Location, goal: Location, env: "Environment"
    ) -> List[Location]:
        # a stars using two weights (g and h) and a priority queue that use the f score which is sum of g and h
        # g is the cost to reach the node from the start node
        # h is the heuristic which is the estimated cost to reach the goal from the node
        """Find the shortest path from start to goal using A* algorithm."""

        def heuristic(a: Location, b: Location) -> int:
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        # Initialize the open set and closed set
        open_set = PriorityQueue()
        open_set.put((0, start))
        came_from = {}
        g_score = {start: 0}
        # calculate h score for all nodes
        h_score = {}

        while not open_set.empty():

            _, current = open_set.get()
            path = []
            path.append(current)

            if self.is_adjacent(current, goal):
                break

            adjacents = self.get_valid_adjacent_cell(
                current, env, include_diagonals=False
            )
            for adjacent in adjacents:
                if adjacent not in g_score:
                    g_score[adjacent] = g_score[current] + 1
                    h_score = heuristic(adjacent, goal)
                    f_score = g_score[adjacent] + h_score
                    open_set.put((f_score, adjacent))

        return came_from
