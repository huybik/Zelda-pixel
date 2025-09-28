import asyncio
from queue import Queue  # Thread-safe queue for communication
import threading
from api import LocalAPI, OpenaiAPI
from settings import INFERENCE_MODE

class AIManager:
    """
    Manages AI API calls in a separate background thread to prevent blocking the main game loop.
    """
    def __init__(self):
        self.request_queue = Queue()
        self.response_dict = {}  # Shared dictionary for results {entity_id: {response_type: response}}
        self._running = True
        self.api = LocalAPI() if INFERENCE_MODE == "local" else OpenaiAPI()

    def run_worker_in_thread(self):
        """Entry point for the thread, runs the async worker."""
        try:
            asyncio.run(self.worker())
        except Exception as e:
            print(f"AI Manager thread encountered an error: {e}")

    async def worker(self):
        """The core worker loop that processes requests from the queue."""
        print("AI Worker started.")
        while self._running:
            if not self.request_queue.empty():
                entity_id, request_type, prompt = self.request_queue.get()
                print(f"AI Worker: Processing '{request_type}' for {entity_id}")
                try:
                    response = await self.api.get_response(user_input=prompt)
                    if entity_id not in self.response_dict:
                        self.response_dict[entity_id] = {}
                    self.response_dict[entity_id][request_type] = response
                    print(f"AI Worker: Got response for {entity_id}")
                except Exception as e:
                    print(f"AI worker error for {entity_id}: {e}")
            else:
                await asyncio.sleep(0.1)  # Sleep briefly to prevent busy-waiting
        print("AI Worker stopped.")

    def start(self):
        """Starts the AI worker in a daemon thread."""
        self.thread = threading.Thread(target=self.run_worker_in_thread, daemon=True)
        self.thread.start()

    def stop(self):
        """Signals the worker to stop."""
        self._running = False

    def request_decision(self, entity_id, prompt):
        """Adds a non-blocking decision request to the queue."""
        self.request_queue.put((entity_id, 'decision', prompt))

    def request_summary(self, entity_id, prompt):
        """Adds a non-blocking summary request to the queue."""
        self.request_queue.put((entity_id, 'summary', prompt))

    def get_response(self, entity_id, response_type):
        """
        Non-blocking check for a response from the main thread.
        Returns the response if available, otherwise None.
        """
        if entity_id in self.response_dict and response_type in self.response_dict[entity_id]:
            return self.response_dict[entity_id].pop(response_type)
        return None
