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
                    # max_tokens=256,
                    # repeat_penalty=1.1,
                    # stop=["END"],
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
    def get_actions(self, last_observation):
        entities = last_observation["nearby_entities"]
        objects = last_observation["nearby_objects"]
        
        target_entities = None
        target_resources = None
        
        if entities:
            target_entities = "".join([entity["entity_name"] for entity in entities])
       
        if objects:
            target_resources = "".join([object["object_name"] for object in objects])
        
            
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
        summary = self.memory.read_last_n_records(summary_file,1)
        
        stream_file = f"stream_{entity.full_name}.json"
        stream_data = self.memory.read_last_n_records(stream_file)
        
        observations = self.get_observations(stream_data)
        target_entities, target_resources = self.get_actions(stream_data[-1])
        
        prompt = f"""
            Context:
            You are {entity.full_name}, and you are {entity.characteristic}.
            Priority to survive using all actions available.
            
            'progress summary': {summary}
            'Observations':
            {observations}
            
            Guidelines for output 'Next step':
            
            
            "action": One from ("attack", "runaway", "heal") target entity or ("mine") resource.
            "target_name": Your target name
            "vigilant": A score from 0 to 100 indicating your current vigilant level.
            "reason": a single sentence.
            
            Can only target following entities:
            {target_entities}
            And can only mine following resources:
            {target_resources}
            If both are empty, set target_name to "None".

            Respond in single JSON with the format of "Next step":{{"action": string,"target_name": string,"vigilant": int,"reason": single sentence}}
            'Next step':
            """
        try:
            response = await self.api.get_response(user_input=prompt)
            try:
                print(f"{entity.full_name} prompt: {prompt}\n")
                
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
   
