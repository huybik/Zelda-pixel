import openai

from openai import OpenAI  # New import
import asyncio
from memstream import MemoryStream
import json
import pygame
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
        player: "Player",
        entities: list["Enemy"],
        objects: list["Tile"],
    ):

        observation = self.memory.save_observation(entity, player, entities, objects)
        memory = self.summary

        prompt = (
            f"You are {entity.full_name} and you are {entity.characteristic}."
            f"Using current 'observation' about the world and your 'memory' to decide what to do next. "
            "Follow the steps to decide what to do next:"
            '1. Decide your next target "target_name":"name", '
            '2. decide your next location with "location":"x,y". If you want to attack the target your next location is target location.'
            "If you want to runaway from the target you should increase distance from target location."
            "If you want to if you want to help the target, you should not attack."
            '3. Decide if you want to attack the target "attack":"yes/no", if you want to help the target you should not attack.'
            '4. Finally your reason for your actions in less than 5 words with "reason":"your reason".  '
            'Output format: {"move": "x,y", "target_name":"name", "attack": "yes/no", "reason": "your reason"} \n\n'
            f"'Observation': {observation}\n"
            f"'Memory': {memory}\n"
            "Your response: "
        )

        try:
            response = await self.api.get_response(user_input=prompt)
            print(f"prompt: {prompt}\n")
            print(f"{entity.full_name} decision: {response} \n")

            self.decision = response

        except Exception as e:
            print(f"Error getting movement decision: {e}")
            # Keep the current direction on error

    async def summary_context(
        self,
        entity: "Enemy",
        player: "Player",
        entities: list["Enemy"],
        objects: list["Tile"],
        threshold=50,
    ):
        memory_stream = self.memory.read_data(f"stream_{entity.full_name}")
        observation = self.memory.save_observation(entity, player, entities, objects)

        prompt = (
            f"You are {entity.full_name} and you are {entity.characteristic}."
            f"your 'observation': {observation}\n"
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

        except (asyncio.TimeoutError, Exception) as e:
            print(f"Error getting movement decision: {e}")
            # Keep the current direction on error

    def parse_decision(self, response):
        try:
            data = json.loads(response)

            coords = data["move"].split(",")
            if len(coords) != 2:
                raise ValueError("Move coordinates must be in format 'x,y'")

            x = float(coords[0].strip())
            y = float(coords[1].strip())

            decision = {
                "target_location": pygame.math.Vector2(x, y),
                "target_name": data["target_name"],
                "reason": data["reason"],
                "want_to_attack": data["attack"].lower() == "yes",
            }

            return decision

        except (json.JSONDecodeError, ValueError, AttributeError, KeyError) as e:
            print(f"Error parsing decision response: {e}")
            return None


if __name__ == "__main__":
    persona = API()
    prompt = """Based on provided memory streams, give a summary of the situation in less than 20 words. Memory stream: "
              2024-11-05 15:14:45,name:bamboo,location:(2592, 1504),health:70/70,status:idle,target:[0, 0],player_distance:296.2,player_pos:(2308, 1420),player_status:down
                2024-11-05 15:14:48,name:bamboo,location:(2542, 1461),health:70/70,status:move,target:[2540, 1460],player_distance:134.5,player_pos:(2409, 1481),player_status:right_idle
                2024-11-05 15:14:51,name:bamboo,location:(2561, 1479),health:45/70,status:move,target:[2500, 1480],player_distance:152.0,player_pos:(2409, 1481),player_status:right_attack
                2024-11-05 15:14:54,name:bamboo,location:(2504, 1476),health:20/70,status:move,target:[2500, 1475],player_distance:95.1,player_pos:(2409, 1481),player_status:right_attack"""
    response = asyncio.run(persona.get_response(prompt))
    print(response)
