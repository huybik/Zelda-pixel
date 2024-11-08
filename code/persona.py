import openai

from openai import OpenAI  # New import
import asyncio
from memstream import MemoryStream

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
            f"You are {entity.monster_name} with id{entity.monster_id} and you are {entity.characteristic} but will attack if threatened. "
            f"Using current 'observation' about the world and your 'memory' to decide what to do next. "
            f'Decide your next location with "location":"x,y" and if you should attack the player with "attack":"yes/no" and your reason for moving in less than 5 words with "reason":"your reason". If you want to attack the player move to the player location.'
            'Output format: {"move": "x,y", "attack": "yes/no", "reason": "your reason"}\n'
            f"'Observation': {observation}\n"
            f"'Memory': {memory}\n"
            "Your response: "
        )
        print(f"prompt: {prompt}\n")
        try:
            response = await self.api.get_response(user_input=prompt)
            print(f"{entity.monster_name}_{entity.monster_id} decision: {response} \n")

            # self.memory.write_data(response, "decision", monster_id)
            self.decision = response

        except Exception as e:
            print(f"Error getting movement decision: {e}")
            # Keep the current direction on error

    async def summary_context(self, entity: "Enemy", threshold=50):
        memory_stream = self.memory.read_data(
            f"stream_{entity.monster_name}_{entity.monster_id}"
        )
        prompt = f"Fetch important events from 'memory stream' then summary them in less than {threshold} words. \n'memory stream': {memory_stream}"

        try:
            response = await self.api.get_response(user_input=prompt)
            print(f"{entity.monster_name}_{entity.monster_id} summary: {response} \n")

            # self.memory.write_data(response, "summary", monster_id)
            self.summary = response

        except (asyncio.TimeoutError, Exception) as e:
            print(f"Error getting movement decision: {e}")
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
