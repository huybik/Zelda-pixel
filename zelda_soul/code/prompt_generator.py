import json
from typing import TYPE_CHECKING
from memstream import MemoryStream
from settings import OBSERVATION_WINDOW, prompt_template, summary_template

if TYPE_CHECKING:
    from enemy import Enemy

class PromptGenerator:
    """
    Handles the creation of dynamic prompts for the AI based on game state.
    """
    def __init__(self, memory_stream: MemoryStream):
        self.memory = memory_stream

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
        if not stream_data:
            return None
        
        summary = self.memory.read_last_n_records(f"summary_{entity.full_name}.json", 1)
        observations = self._get_observations_for_prompt(stream_data)
        target_entities, target_resources = self._get_actions(stream_data[-1])

        return prompt_template.format(
            full_name=entity.full_name,
            characteristic=entity.characteristic,
            observation=observations.replace('{', '[').replace('}', ']'),
            summary=str(summary).replace('{', '[').replace('}', ']'),
            target_entities=target_entities,
            target_resources=target_resources
        )

    def format_summary_prompt(self, entity: "Enemy", threshold=50) -> str | None:
        """Formats the prompt for the AI to summarize its memory."""
        stream_data = self.memory.read_last_n_records(f"stream_{entity.full_name}.json")
        if not stream_data:
            return None

        progress = self._get_progress_for_summary(stream_data)
        summary = self.memory.read_last_n_records(f"summary_{entity.full_name}.json", 1)
        
        return summary_template.format(
            memory_stream=progress,
            summary=summary,
            threshold=threshold,
        )