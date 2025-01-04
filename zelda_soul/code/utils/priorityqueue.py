import heapq

import heapq

class PriorityQueueWithUpdate:
    def __init__(self):
        self.heap = []  # The heap to maintain priority order
        self.counter = 0  # Counter to handle task versioning
        self.entry_finder = {}  # Mapping of tasks to their heap entries
        self.REMOVED = '<removed-task>'  # Placeholder for removed tasks
    
    def put(self, priority, task):
        """Add a new task or update the priority of an existing task."""
        if task in self.entry_finder:
            self.remove_task(task)
        count = self.counter
        self.counter += 1
        entry = [priority, count, task]
        self.entry_finder[task] = entry
        heapq.heappush(self.heap, entry)
    
    def has(self, task):
        """Check if the task exists in the queue."""
        return task in self.entry_finder and self.entry_finder[task][-1] != self.REMOVED
    
    def remove_task(self, task):
        """Mark a task as removed without actually removing it from the heap."""
        entry = self.entry_finder.pop(task, None)
        if entry:
            entry[-1] = self.REMOVED

    def get(self):
        """Remove and return the lowest-priority task."""
        while self.heap:
            priority, count, task = heapq.heappop(self.heap)
            if task is not self.REMOVED:
                del self.entry_finder[task]
                return priority, task
        raise KeyError('pop from an empty priority queue')
    
    def qsize(self):
        """Return the number of valid tasks in the queue."""
        return len(self.entry_finder)
    
    def empty(self):
        """Check if the queue is empty."""
        return not self.entry_finder    
# # Example usage:
# pq = PriorityQueueWithUpdate()

# # Adding tasks
# pq.put('task1', 1)
# pq.put('task2', 2)
# pq.put('task3', 3)

# # Update the priority of 'task2'
# pq.put('task2', 0)

# # Retrieve tasks by priority
# print(pq.get())  # 'task2' with priority 0
# print(pq.get())  # 'task1' with priority 1
# print(pq.get())  # 'task3' with priority 3