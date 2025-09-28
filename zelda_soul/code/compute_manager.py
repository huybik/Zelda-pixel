# ./zelda_soul/code/compute_manager.py
import threading
from queue import Queue, Empty
import time
from collections import namedtuple
from queue import PriorityQueue
import pygame

# Task definition for compute jobs
Task = namedtuple('Task', ['owner_id', 'type', 'data'])

class ComputeManager:
    """
    Manages CPU-intensive, blocking computations in a separate background thread
    to prevent blocking the main game loop.
    """
    def __init__(self):
        self.request_queue = Queue()
        self.response_dict = {}  # {owner_id: {response_type: response}}
        self._running = True
        self.thread = None

        # Map task types to handler functions
        self.handlers = {
            'pathfinding': self._astar_pathfinding,
        }

    def start(self):
        """Starts the compute worker in a daemon thread."""
        self.thread = threading.Thread(target=self.worker, daemon=True)
        self.thread.start()

    def stop(self):
        """Signals the worker to stop and waits for it to finish."""
        self._running = False
        if self.thread:
            self.thread.join()

    def request(self, owner_id, request_type, data):
        """Adds a generic, non-blocking compute request to the queue."""
        if request_type in self.handlers:
            task = Task(owner_id=owner_id, type=request_type, data=data)
            self.request_queue.put(task)
        else:
            print(f"ComputeManager: Unknown request type '{request_type}'")

    def get_response(self, owner_id, response_type):
        """
        Non-blocking check for a response from the main thread.
        Returns the response if available, otherwise None.
        """
        if owner_id in self.response_dict and response_type in self.response_dict[owner_id]:
            return self.response_dict[owner_id].pop(response_type)
        return None

    def worker(self):
        """The core worker loop that processes tasks from the queue."""
        print("Compute Worker started.")
        while self._running:
            try:
                task = self.request_queue.get(timeout=0.1)
                handler = self.handlers.get(task.type)
                if handler:
                    try:
                        result = handler(task.data)
                        if task.owner_id not in self.response_dict:
                            self.response_dict[task.owner_id] = {}
                        self.response_dict[task.owner_id][task.type] = result
                    except Exception as e:
                        print(f"Compute worker error processing {task.type} for {task.owner_id}: {e}")
            except Empty:
                continue
            except Exception as e:
                print(f"Compute Manager thread encountered an error: {e}")
        print("Compute Worker stopped.")
    
    def _astar_pathfinding(self, data):
        """
        Calculates a path using the A* algorithm.
        All data is provided via the 'data' dictionary.
        """
        start_pos = data['start_pos']
        goal_pos = data['goal_pos']
        obstacle_hitboxes = data['obstacles']
        tile_size = data['tile_size']

        def to_grid(pos, ts): return (int(pos.x // ts), int(pos.y // ts))
        def to_world(grid, ts): return pygame.math.Vector2(grid[0] * ts + ts / 2, grid[1] * ts + ts / 2)
        def get_occupied_grids(rect, ts):
            grids = set()
            for x in range(int(rect.left // ts), int(rect.right // ts) + 1):
                for y in range(int(rect.top // ts), int(rect.bottom // ts) + 1):
                    grids.add((x, y))
            return grids

        start_grid, goal_grid = to_grid(start_pos, tile_size), to_grid(goal_pos, tile_size)
        obstacle_grids = set().union(*(get_occupied_grids(hitbox, tile_size) for hitbox in obstacle_hitboxes))
        
        if goal_grid in obstacle_grids:
            found_new_goal = False
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                neighbor = (goal_grid[0] + dx, goal_grid[1] + dy)
                if neighbor not in obstacle_grids:
                    goal_grid, found_new_goal = neighbor, True
                    break
            if not found_new_goal: return []

        def heuristic(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
        open_set, came_from, g_score = PriorityQueue(), {}, {start_grid: 0}
        open_set.put((0, start_grid))
        f_score = {start_grid: heuristic(start_grid, goal_grid)}
        
        while not open_set.empty():
            _, current_grid = open_set.get()
            if current_grid == goal_grid:
                path = []
                while current_grid in came_from:
                    path.append(to_world(current_grid, tile_size))
                    current_grid = came_from[current_grid]
                path.reverse(); return path
            
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (current_grid[0] + dx, current_grid[1] + dy)
                if neighbor in obstacle_grids: continue
                tentative_g_score = g_score.get(current_grid, float('inf')) + 1
                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor], g_score[neighbor] = current_grid, tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal_grid)
                    open_set.put((f_score[neighbor], neighbor))
        return []