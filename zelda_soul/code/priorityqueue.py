import heapq

class PriorityQueueWithUpdate:
    def __init__(self):
        self.heap = []  # The heap to maintain priority order
        self.counter = 0  # Counter to handle task versioning
        self.entry_finder = {}  # Mapping of tasks to their heap entries
        self.REMOVED = '<removed-task>'  # Placeholder for removed tasks
    
    def put(self,  priority, task):
        # Add a new task or update an existing task
        if id(task) in self.entry_finder:
            self.remove_task(task)
        count = self.counter
        self.counter += 1
        entry = [priority, count, task]
        self.entry_finder[id(task)] = entry
        heapq.heappush(self.heap, entry)
    
    def is_in(self, task):
        if id(task) in self.entry_finder:
            return True
        return False
    
    def remove_task(self, task):
        # Mark a task as removed
        entry = self.entry_finder.pop(id(task))
        entry[-1] = self.REMOVED

    def get(self):
        # Pop the smallest task
        while self.heap:
            priority, count, task = heapq.heappop(self.heap)
            if task is not self.REMOVED:
                del self.entry_finder[id(task)]
                return priority, task
        raise KeyError('pop from an empty priority queue')
    
    def qsize(self):
        return len(self.entry_finder)
    
    def empty(self):
        return not bool(self.entry_finder)    
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