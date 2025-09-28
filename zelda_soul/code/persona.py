import json
import re
import time
from memstream import MemoryStream
from prompt_generator import PromptGenerator  # Updated import

class Persona:
    """
    A helper class for parsing AI responses and managing memory summaries.
    Delegates prompt creation to the PromptGenerator.
    """
    def __init__(self):
        self.memory = MemoryStream()
        self.prompt_generator = PromptGenerator(self.memory)

    def parse_decision_response(self, response: str) -> dict:
        """Cleans and parses the raw JSON string from the API."""
        raw = response.strip()
        if raw.startswith("```"):
            raw = raw.strip("`\n ")
            parts = raw.split("\n", 1)
            if len(parts) == 2 and not parts[0].strip().startswith("{"):
                raw = parts[1]
        
        obj_match = re.search(r"\{.*\}", raw, re.DOTALL)
        candidate = obj_match.group(0) if obj_match else raw
        
        if '"Next step"' in candidate:
            try:
                outer = json.loads(candidate)
                if isinstance(outer, dict) and "Next step" in outer:
                    candidate = json.dumps(outer["Next step"], ensure_ascii=False)
            except Exception:
                pass

        print(f"Parsing decision: {candidate}")
        return json.loads(candidate)

    def save_summary(self, entity_id: str, summary_text: str):
        """Persists the AI-generated summary in the long-term memory store."""
        entry = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "summary": summary_text}
        self.memory.write_summary(entity_id, entry)
