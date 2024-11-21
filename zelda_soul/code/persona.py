import openai

from openai import OpenAI  # New import
import asyncio
from memstream import MemoryStream
import json
import pygame
from settings import  MODEL_PATH, CONTEXT_LENGTH, prompt_template, GPU, summary_template
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from enemy import Enemy
    from player import Player
    from tile import Tile


from llama_cpp import Llama
import time



class API:
    def __init__(self, mode: str = "local"):
        self.system_prompt = """You are an smart being that like to plan your action"""
        self.mode = mode
        if self.mode == "local":
            self.client = Llama(model_path=MODEL_PATH,
            # n_threads=8,
            n_ctx=CONTEXT_LENGTH,
            verbose=True,
            n_gpu_layers=-1, 
            use_mlock=True,
            # use_mmap=True,
            
            n_batch=226,
            seed=42,
            )
        else:
            
            self.model = "gpt-4o-mini"  # Using GPT-4 Mini model
            self.client = None  # Add client property
            self.load_api_key()
            

    async def get_response(self, user_input, system_prompt=None):
        if not system_prompt:
            system_prompt = self.system_prompt
        
        
        
        messages=[
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_input}
        ]
        
        try:
            loop = asyncio.get_event_loop()
            current = time.time()
            if self.mode == "local":
                
                response = await loop.run_in_executor(
                None,  # None uses the default executor
                lambda: self.client.create_chat_completion(
                    messages=messages,
                    temperature=0,
                    # max_tokens=128,
                    # repeat_penalty=1.5,
                    )
                )
                ai_response = response["choices"][0]["message"]["content"].strip()
            else:
                response = await loop.run_in_executor(
                    None,  # None uses the default executor
                    lambda: self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": user_input}],
                    ),
                )
                ai_response = response.choices[0].message.content
                

            # print(ai_response)
            print(f"Time taken: {time.time() - current}")
            
            return ai_response

        except Exception as e:
            print(f"Error getting response: {e}")
            return "I'm having trouble connecting right now."

    def load_api_key(self):
        import os

        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)  # Initialize client with API key
            else:
                print("Error: OPENAI_API_KEY not found in environment variables")
                return None
        except Exception as e:
            print(f"Error loading API key: {e}")
            return None


class Persona:
    def __init__(self, api):
        self.api = api
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
        observation = self.memory.read_last_n_observations(entity, 1)

        prompt = prompt_template.format(
            full_name=entity.full_name,
            characteristic=entity.characteristic,
            summary=summary,
            observation=observation,
        )

        try:
            response = await self.api.get_response(user_input=prompt)
            # print(f"prompt: {prompt}\n")
            try:
                response = '{' + response.split('{')[-1].split('}')[0] + '}'
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
        memory_stream = self.memory.read_last_n_observations(entity, 3)
        summary = self.memory.read_summary(entity)
        # observation = self.memory.read_last_n_observations(entity, 1)

        prompt = summary_template.format(memory_stream=memory_stream,
                              threshold=threshold,
                              summary = summary)
            
        try:
            # print(f"prompt: {prompt}\n")
            response = await self.api.get_response(user_input=prompt)
            print(f"{entity.full_name} summary: {response} \n")

            # self.memory.write_data(response, "summary", full_name)
            self.summary = response
            filename = f"summary_{entity.full_name}"
            self.memory.write_data(filename, response)
            
            return

        except Exception as e:
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
