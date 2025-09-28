from memstream import MemoryStream
import json
from typing import TYPE_CHECKING
from settings import MEMORY_SIZE, OBSERVATION_WINDOW, prompt_template, summary_template
from api import OpenaiAPI, LocalAPI
import time

if TYPE_CHECKING:
    from enemy import Enemy


class Persona:
    def __init__(self, model="gpt"):
        if model == "gpt":
            self.api = OpenaiAPI()
        elif model == "local":
            self.api = LocalAPI()

        self.memory = MemoryStream()

        self.decision = None
        self.summary = None

        # actions

    def get_actions(self, last_observation):
        entities = last_observation["nearby_entities"]
        objects = last_observation["nearby_objects"]

        target_entities = None
        target_resources = None

        if entities:
            target_entities = ",".join([entity["entity_name"] for entity in entities])

        if objects:
            target_resources = ",".join([object["object_name"] for object in objects])

        return target_entities, target_resources

    def get_observations(self, observations):
        # Keep only last OBSERVATION_WINDOW entries to reduce prompt tokens
        window = observations[-OBSERVATION_WINDOW:] if observations else []
        result = [
            {
                "t": entry["timestamp"],
                "obs": entry["self"].get("observations"),
            }
            for entry in window
        ]
        return json.dumps(result, ensure_ascii=False)

    def get_progress(self, observations):
        window = observations[-(OBSERVATION_WINDOW * 2):] if observations else []
        result = [
            {
                "t": entry["timestamp"],
                "obs": entry["self"].get("observations"),
                "stats": entry["self"].get("stats"),
            }
            for entry in window
        ]
        return json.dumps(result, ensure_ascii=False)

    async def fetch_decision(
        self,
        entity: "Enemy",
    ):

        # observation = self.memory.save_observation(entity, player, entities, objects)
        summary_file = f"summary_{entity.full_name}.json"
        summary = self.memory.read_last_n_records(summary_file, 1)

        stream_file = f"stream_{entity.full_name}.json"
        stream_data = self.memory.read_last_n_records(stream_file)

        observations = self.get_observations(stream_data)
        target_entities, target_resources = self.get_actions(stream_data[-1])

        prompt = prompt_template.format(
            full_name=entity.full_name,
            characteristic=entity.characteristic,
            observation=observations.replace('{', '[').replace('}', ']'),
            summary=str(summary).replace('{', '[').replace('}', ']'),
        ) + f"\nTargets: entities={target_entities} resources={target_resources}"
        try:
            response = await self.api.get_response(user_input=prompt)
            try:
                print(f"{entity.full_name} prompt: {prompt}\n")
                raw = response.strip()
                # Normalize fenced or triple backtick content
                if raw.startswith("```"):
                    raw = raw.strip("`\n ")
                    # remove possible language tag like json
                    parts = raw.split("\n", 1)
                    if len(parts) == 2 and not parts[0].lstrip().startswith("{"):
                        raw = parts[1]
                # Extract first JSON object greedily
                import re
                obj_match = re.search(r"\{.*\}", raw, re.DOTALL)
                candidate = obj_match.group(0) if obj_match else raw
                # If wrapped like {"Next step": {...}} unwrap
                if '"Next step"' in candidate:
                    try:
                        outer = json.loads(candidate)
                        if isinstance(outer, dict) and "Next step" in outer:
                            candidate = json.dumps(outer["Next step"], ensure_ascii=False)
                    except Exception:
                        pass
                print(f"{entity.full_name} decision raw: {candidate} \n")
                data = json.loads(candidate)
                self.decision = data
                return
            except json.JSONDecodeError:
                print("Error parse decision JSON")

        except Exception as e:
            print(f"Error getting decision: {e}")
            # Keep the current direction on error

    async def summary_context(
        self,
        entity: "Enemy",
        threshold=50,
    ):
        # memory_stream = self.memory.read_memory(entity)
        stream_file = f"stream_{entity.full_name}.json"
        stream_data = self.memory.read_last_n_records(stream_file)
        progress = self.get_progress(stream_data)

        summary_file = f"summary_{entity.full_name}.json"
        summary = self.memory.read_last_n_records(summary_file, 1)

        # memory_stream = self.memory.read_last_n_records(memory_file, 2)
        # memory_stream = self.memory.read_last_n_records(memory_file, OBSERVATION_TO_SUMMARY)

        prompt = summary_template.format(
            memory_stream=progress,
            summary=summary,
            threshold=threshold,
        )

        print(prompt)
        try:
            # print(f"prompt: {prompt}\n")
            response = await self.api.get_response(user_input=prompt)
            # print(f"{entity.full_name} summary: {response} \n")

            # self.memory.write_data(response, "summary", full_name)
            self.summary = response.strip()

            filename = f"summary_{entity.full_name}.json"
            self.save_summary(response, filename, threshold=MEMORY_SIZE)

            return

        except Exception as e:
            print(f"Error getting summary: {e}")
            # Keep the current direction on error

    def save_summary(self, entry, filename, threshold=MEMORY_SIZE):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        entry = {"timestamp": timestamp, "summary": entry}

        self.memory.write_memory(entry, filename, threshold=threshold)
