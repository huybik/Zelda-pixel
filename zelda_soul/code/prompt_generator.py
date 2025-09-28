import json
from typing import TYPE_CHECKING
from .memstream import MemoryStream
from .settings import OBSERVATION_WINDOW, SUMMARY_HISTORY_LIMIT, prompt_template, summary_template

if TYPE_CHECKING:
    from .enemy import Enemy

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

    def _ensure_short_term(self, entity: "Enemy") -> list[dict]:
        """Guarantee short-term observations are populated for a prompt build."""
        observations = list(entity.short_term_memory)
        if observations:
            return observations
        fallback = self.memory.read_recent(entity.full_name, OBSERVATION_WINDOW)
        for record in fallback:
            entity.short_term_memory.append(record)
        return list(entity.short_term_memory)

    def format_decision_prompt(self, entity: "Enemy", metadata: dict | None = None) -> str | None:
        """Formats the prompt for the AI to make a decision."""
        observations = self._ensure_short_term(entity)
        if not observations:
            return None
        window = observations[-OBSERVATION_WINDOW:]
        target_entities, target_resources = self._get_actions(window[-1])

        summary_entry = self.memory.read_last_summary(entity.full_name) or {}

        keywords = []
        if metadata:
            target = metadata.get("target") or metadata.get("target_name")
            if target:
                keywords.append(str(target))
            trigger = metadata.get("trigger")
            if trigger:
                keywords.append(str(trigger))

        relevant_memories = self.memory.query_observations(entity.full_name, keywords, limit=OBSERVATION_WINDOW)

        return prompt_template.format(
            full_name=entity.full_name,
            characteristic=entity.characteristic,
            observations=json.dumps(window, ensure_ascii=False),
            summary=json.dumps(summary_entry, ensure_ascii=False),
            relevant_memories=json.dumps(relevant_memories, ensure_ascii=False),
            target_entities=target_entities,
            target_resources=target_resources,
            context=json.dumps(metadata or {}, ensure_ascii=False),
        )

    def format_summary_prompt(self, entity: "Enemy", threshold=50) -> str | None:
        """Formats the prompt for the AI to summarize its memory."""
        self._ensure_short_term(entity)
        recent_progress = self.memory.read_recent(entity.full_name, OBSERVATION_WINDOW * 2)
        if not recent_progress:
            return None
        summaries = self.memory.read_recent(entity.full_name, SUMMARY_HISTORY_LIMIT, entry_type="summary")

        return summary_template.format(
            memory_stream=json.dumps(recent_progress, ensure_ascii=False),
            summary=json.dumps(summaries, ensure_ascii=False),
            threshold=threshold,
        )
