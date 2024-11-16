import openai

from openai import OpenAI  # New import
import asyncio
from memstream import MemoryStream
import json
import pygame
from settings import default_actionable, output_format
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from enemy import Enemy
    from player import Player
    from tile import Tile


class API:
    def __init__(self):
        self.model = "gpt-4o-mini"  # Using GPT-4 Mini model
        self.messages = []
        self.client = None  # Add client property
        self.load_api_key()

    async def get_response(self, user_input, system_prompt=None):
        if system_prompt and not self.messages:
            # Add system prompt at the start of conversation
            # self.messages.append({"role": "system", "content": system_prompt})
            pass

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,  # None uses the default executor
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": user_input}],
                ),
            )
            # response = self.client.chat.completions.create(
            #     model=self.model, messages=self.messages
            # )
            ai_response = response.choices[0].message.content
            # print(response.usage)
            # self.messages.append({"role": "assistant", "content": ai_response})

            return ai_response

        except Exception as e:
            print(f"Error getting response: {e}")
            return "I'm having trouble connecting right now."

    def load_api_key(self):
        try:
            with open("../openai-key.txt", "r") as file:
                api_key = file.read().strip()
                self.client = OpenAI(api_key=api_key)  # Initialize client with API key
        except FileNotFoundError:
            print("Error: openai-key.txt file not found")
            return None
        except Exception as e:
            print(f"Error loading API key: {e}")
            return None


class Persona:
    def __init__(self):
        self.api = API()
        self.memory = MemoryStream()

        self.decision = None
        self.summary = None

        # actions

    async def fetch_decision(
        self,
        entity: "Enemy",
    ):

        # observation = self.memory.save_observation(entity, player, entities, objects)
        summary = self.memory.read_summary(entity)
        observation = self.memory.read_last_n_observations(entity, 3)

        prompt = (
            f"Using your last 'Observation' about the world and your 'Memory', decide next step to fullfil your 'Motive' "
            "aggression: your aggressive score from 0 to 100. "
            f"action: attack or runaway from enemy, heal ally, mine trees. "
            "target_name: your action need a target, write it's name. or 'None' if you cant find your target"
            "reason: reason for your action less than 5 words.\n "
            f"You are {entity.full_name} and you are {entity.characteristic}.\n"
            f"'Motive': {default_actionable}.\n"
            f"'Observation': {observation}\n"
            f"'Memory': {summary}\n"
            f"Output next step in format: {output_format} \n"
            "Your next step: "
        )

        try:
            response = await self.api.get_response(user_input=prompt)
            print(f"prompt: {prompt}\n")
            print(f"{entity.full_name} decision: {response} \n")
            try:
                data = json.loads(response)
                self.decision = data
            except json.JSONDecodeError:
                print("Error load json")

        except Exception as e:
            print(f"Error getting decision: {e}")
            # Keep the current direction on error

    async def summary_context(
        self,
        entity: "Enemy",
        threshold=100,
    ):
        memory_stream = self.memory.read_memory(entity)
        observation = self.memory.read_last_n_observations(entity, 3)

        prompt = (
            f"You are {entity.full_name} and you are {entity.characteristic}."
            f"your current 'observation': {observation}\n"
            f"your 'memory stream': {memory_stream}\n"
            "\nDo this step by step:\n"
            "1. Fetch the most relevance, recency, and importance records events from 'memory stream' related to your current 'observation'."
            f"2. Summary them in less than {threshold} words so that you can understand the situation."
            f"Your summary: "
        )

        try:
            response = await self.api.get_response(user_input=prompt)
            print(f"{entity.full_name} summary: {response} \n")

            # self.memory.write_data(response, "summary", full_name)
            self.summary = response
            filename = f"summary_{entity.full_name}"
            self.memory.write_data(filename, response)

        except (asyncio.TimeoutError, Exception) as e:
            print(f"Error getting summary: {e}")
            # Keep the current direction on error


if __name__ == "__main__":
    persona = API()
    prompt = """Based on provided memory streams, give a summary of the situation in less than 20 words. Memory stream: "
              2024-11-05 15:14:45,name:bamboo,location:(2592, 1504),health:70/70,status:idle,target:[0, 0],player_distance:296.2,player_pos:(2308, 1420),player_status:down
                2024-11-05 15:14:48,name:bamboo,location:(2542, 1461),health:70/70,status:move,target:[2540, 1460],player_distance:134.5,player_pos:(2409, 1481),player_status:right_idle
                2024-11-05 15:14:51,name:bamboo,location:(2561, 1479),health:45/70,status:move,target:[2500, 1480],player_distance:152.0,player_pos:(2409, 1481),player_status:right_attack
                2024-11-05 15:14:54,name:bamboo,location:(2504, 1476),health:20/70,status:move,target:[2500, 1475],player_distance:95.1,player_pos:(2409, 1481),player_status:right_attack"""
    response = asyncio.run(persona.get_response(prompt))
    print(response)
