import openai

from openai import OpenAI  # New import
import asyncio
from memstream import MemoryStream
import json
import pygame
from settings import  MODEL_PATH, CONTEXT_LENGTH, prompt_template, GPU, summary_template, OBSERVATION_TO_SUMMARY, SUMMARY_SIZE, MEMORY_SIZE
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
        summary_file = f"summary_{entity.full_name}.json"
        observation_file = f"stream_{entity.full_name}.json"
        summary = self.memory.read_last_n_records(summary_file,1)
        observation = self.memory.read_last_n_records(observation_file, 1)

        prompt = prompt_template.format(
            full_name=entity.full_name,
            characteristic=entity.characteristic,
            summary=summary,
            # observation=None,
            observation=observation,
        )

        try:
            response = await self.api.get_response(user_input=prompt)
            try:
                # print(f"prompt: {prompt}\n")
                
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
        memory_file = f"stream_{entity.full_name}.json"
        summary_file = f"summary_{entity.full_name}.json"
        
        memory_stream = self.memory.read_last_n_records(memory_file, 1)
        # memory_stream = self.memory.read_last_n_records(memory_file, OBSERVATION_TO_SUMMARY)
        summary = self.memory.read_last_n_records(summary_file, 1)

        prompt = summary_template.format(memory_stream=memory_stream,
                              summary = summary,
                              threshold=threshold,
                              )
            
        try:
            # print(f"prompt: {prompt}\n")
            response = await self.api.get_response(user_input=prompt)
            print(f"{entity.full_name} summary: {response} \n")

            # self.memory.write_data(response, "summary", full_name)
            self.summary = response
            
            filename = f"summary_{entity.full_name}.json"
            self.save_summary(response,filename, threshold=MEMORY_SIZE)
            
            return

        except Exception as e:
            print(f"Error getting summary: {e}")
            # Keep the current direction on error

    

    def save_summary(self, entry, filename, threshold=MEMORY_SIZE):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        entry = {
            "timestamp": timestamp,
            "summary": entry
        }
        
        
        self.memory.write_memory(entry, filename, threshold=threshold)
   
