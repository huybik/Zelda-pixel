from memstream import MemoryStream
import json
import re
import time
from typing import TYPE_CHECKING
from settings import MEMORY_SIZE, OBSERVATION_WINDOW, prompt_template, summary_template

if TYPE_CHECKING:
    from enemy import Enemy

class Persona:
    """A synchronous helper class for formatting AI prompts and parsing responses."""
    def __init__(self):
        self.memory = MemoryStream()

    def _get_actions(self, last_observation):
        entities = last_observation.get("nearby_entities", [])
        objects = last_observation.get("nearby_objects", [])
        target_entities = ",".join([e["entity_name"] for e in entities]) if entities else "None"
        target_resources = ",".join([o["object_name"] for o in objects]) if objects else "None"
        return target_entities, target_resources

    def _get_observations_for_prompt(self, observations):
        window = observations[-OBSERVATION_WINDOW:] if observations else []
        result = [{"t": e["timestamp"], "obs": e["self"].get("observations")} for e in window]
        return json.dumps(result, ensure_ascii=False)

    def _get_progress_for_summary(self, observations):
        window = observations[-(OBSERVATION_WINDOW * 2):] if observations else []
        result = [{"t": e["timestamp"], "obs": e["self"].get("observations"), "stats": e["self"].get("stats")} for e in window]
        return json.dumps(result, ensure_ascii=False)

    def format_decision_prompt(self, entity: "Enemy") -> str | None:
        """Formats the prompt for the AI to make a decision."""
        stream_data = self.memory.read_last_n_records(f"stream_{entity.full_name}.json")
        if not stream_data: return None
        
        summary = self.memory.read_last_n_records(f"summary_{entity.full_name}.json", 1)
        observations = self._get_observations_for_prompt(stream_data)
        target_entities, target_resources = self._get_actions(stream_data[-1])

        prompt = prompt_template.format(
            full_name=entity.full_name,
            characteristic=entity.characteristic,
            observation=observations.replace('{', '[').replace('}', ']'),
            summary=str(summary).replace('{', '[').replace('}', ']'),
        ) + f"\nTargets: entities={target_entities} resources={target_resources}"
        return prompt

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
            except Exception: pass

        print(f"Parsing decision: {candidate}")
        return json.loads(candidate)

    def format_summary_prompt(self, entity: "Enemy", threshold=50) -> str | None:
        """Formats the prompt for the AI to summarize its memory."""
        stream_data = self.memory.read_last_n_records(f"stream_{entity.full_name}.json")
        if not stream_data: return None

        progress = self._get_progress_for_summary(stream_data)
        summary = self.memory.read_last_n_records(f"summary_{entity.full_name}.json", 1)
        
        prompt = summary_template.format(
            memory_stream=progress,
            summary=summary,
            threshold=threshold,
        )
        return prompt

    def save_summary(self, summary_text: str, filename: str, threshold=MEMORY_SIZE):
        """Saves the AI-generated summary to a file."""
        entry = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "summary": summary_text}
        self.memory.write_memory(entry, filename, threshold=threshold)
