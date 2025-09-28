import asyncio
import json
import threading
from api import API
from settings import INFERENCE_MODE
from collections import namedtuple
from persona import Persona
from priorityqueue import PriorityQueueWithUpdate

# A structured way to define AI tasks
Task = namedtuple('Task', ['entity_id', 'type', 'prompt', 'metadata'])

class AIManager:
    """
    Manages AI API calls in a separate background thread to prevent blocking the main game loop.
    Processes tasks from a queue for enhanced flexibility.
    """
    def __init__(self):
        self.request_queue = PriorityQueueWithUpdate()
        self.response_dict = {}  # {entity_id: {response_type: response}}
        self._running = True
        self.api = API(mode=INFERENCE_MODE)  # Use the unified API
        self.persona = Persona()

    def run_worker_in_thread(self):
        """Entry point for the thread, runs the async worker."""
        try:
            asyncio.run(self.worker())
        except Exception as e:
            print(f"AI Manager thread encountered an error: {e}")

    async def worker(self):
        """The core worker loop that processes tasks from the queue."""
        print("AI Worker started.")
        while self._running:
            if not self.request_queue.empty():
                try:
                    priority, task = self.request_queue.get()
                except KeyError:
                    await asyncio.sleep(0.05)
                    continue
                print(f"AI Worker: Processing '{task.type}' for {task.entity_id} (priority={priority})")
                try:
                    response_text = await self.api.get_response(user_input=task.prompt)
                    if task.entity_id not in self.response_dict:
                        self.response_dict[task.entity_id] = {}
                    
                    # Parse decision responses directly in the worker thread
                    if task.type == 'decision':
                        try:
                            parsed_response = self.persona.parse_decision_response(response_text)
                            self.response_dict[task.entity_id][task.type] = parsed_response
                        except Exception as e:
                            print(f"AI worker failed to parse decision for {task.entity_id}: {e} | Raw: {response_text}")
                            self.response_dict[task.entity_id][task.type] = None
                    else:  # For summaries or other text-based responses
                        self.response_dict[task.entity_id][task.type] = response_text
                        
                    print(f"AI Worker: Got response for {task.entity_id}")
                except Exception as e:
                    print(f"AI worker error for {task.entity_id}: {e}")
            else:
                await asyncio.sleep(0.1)
        print("AI Worker stopped.")

    def start(self):
        """Starts the AI worker in a daemon thread."""
        self.thread = threading.Thread(target=self.run_worker_in_thread, daemon=True)
        self.thread.start()

    def stop(self):
        """Signals the worker to stop."""
        self._running = False

    def request(self, entity_id, request_type, prompt, priority: int = 5, metadata: dict | None = None):
        """Adds a generic, non-blocking request to the queue."""
        if prompt:
            serialized_metadata = None
            if metadata:
                try:
                    serialized_metadata = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
                except TypeError:
                    serialized_metadata = json.dumps(str(metadata))
            task = Task(entity_id=entity_id, type=request_type, prompt=prompt, metadata=serialized_metadata)
            self.request_queue.put(priority, task)

    def get_response(self, entity_id, response_type):
        """
        Non-blocking check for a response from the main thread.
        Returns the response if available, otherwise None.
        """
        if entity_id in self.response_dict and response_type in self.response_dict[entity_id]:
            return self.response_dict[entity_id].pop(response_type)
        return None
