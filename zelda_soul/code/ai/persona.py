from memstream import MemoryStream
import json
from typing import TYPE_CHECKING
from settings import MEMORY_SIZE
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
        result = [
            {
                "timestamp": entry["timestamp"],
                "observations": entry["self"].get("observations"),
            }
            for entry in observations
        ]

        return json.dumps(result)

    def get_progress(self, observations):
        result = [
            {
                "timestamp": entry["timestamp"],
                "observations": entry["self"].get("observations"),
                "stats": entry["self"].get("stats"),
            }
            for entry in observations
        ]

        return json.dumps(result)

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

        prompt = f"""
            Context:
            You are {entity.full_name}, and you are {entity.characteristic}.
            
            'progress summary': {summary}
            'Observations':
            {observations}
            
            
            
            Can only interact with target entities:
            {target_entities}
            And can only mine target resources:
            {target_resources}
            Else target_name to "None" if no target.
            
            Next step explain:

            "action": Chose one from ("attack", "runaway", "heal") target entity or ("mine") target resource. You cant heal yourself.
            "target_name": Your target name
            "vigilant": A score from 0 to 100 indicating your current vigilant level.
            "reason": less than 5 words.

            Respond in single JSON with the format of "Next step":{{"action": string,"target_name": string,"vigilant": int,"reason": reason}}
            'Next step':
            """
        try:
            response = await self.api.get_response(user_input=prompt)
            try:
                print(f"{entity.full_name} prompt: {prompt}\n")

                response = "{" + response.split("{")[-1].split("}")[0] + "}"
                print(f"{entity.full_name} decision: {response} \n")

                data = json.loads(response)
                self.decision = data

                return
            except json.JSONDecodeError:
                print("Error load json")

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

        prompt = f"""
            Context:
            'history':{progress}
            'last summary': {summary}
            
            Summarize your thought in plan text in short paragraph less than {threshold} words.
            'Your thought': """

        print(prompt)
        try:
            # print(f"prompt: {prompt}\n")
            response = await self.api.get_response(user_input=prompt)
            # print(f"{entity.full_name} summary: {response} \n")

            # self.memory.write_data(response, "summary", full_name)
            self.summary = response

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
