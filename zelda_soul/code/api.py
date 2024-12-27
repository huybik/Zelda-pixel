from openai import OpenAI  # New import
import asyncio
from llama_cpp import Llama
from settings import MODEL_PATH, CONTEXT_LENGTH

# import google.generativeai as genai
import time


SYSTEM_PROMPT = """You are an smart being that like to plan your action"""


class LocalAPI:
    def __init__(self):
        self.client = Llama(
            model_path=MODEL_PATH,
            # n_threads=8,
            n_ctx=CONTEXT_LENGTH,
            verbose=True,
            n_gpu_layers=-1,
            use_mlock=True,
            # use_mmap=True,
            n_batch=226,
            seed=42,
        )

    async def get_response(self, user_input):

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

        try:
            loop = asyncio.get_event_loop()
            current = time.time()

            response = await loop.run_in_executor(
                None,  # None uses the default executor
                lambda: self.client.create_chat_completion(
                    messages=messages,
                    temperature=0,
                    # max_tokens=256,
                    # repeat_penalty=1.1,
                    # stop=["END"],
                ),
            )
            ai_response = response["choices"][0]["message"]["content"].strip()

            print(f"Time taken: {time.time() - current}")

            return ai_response

        except Exception as e:
            print(f"Error getting response: {e}")
            return "I'm having trouble connecting right now."


class OpenaiAPI:
    def __init__(self, *args, **kwargs):
        self.system_prompt = """You are an smart being that like to plan your action"""

        self.model = "gpt-4o-mini"  # Using GPT-4 Mini model
        self.client = self.load_api_key()

    async def get_response(self, user_input, system_prompt=None):
        if not system_prompt:
            system_prompt = self.system_prompt

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,  # None uses the default executor
                lambda: self.client.chat.completions.create(
                    model=self.model, messages=messages
                ),
            )
            ai_response = response.choices[0].message.content

            return ai_response

        except Exception as e:
            print(f"Error getting response: {e}")
            return "I'm having trouble connecting right now."

    def load_api_key(self):
        import os

        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                client = OpenAI(api_key=api_key)  # Initialize client with API key
                return client
            else:
                print("Error: OPENAI_API_KEY not found in environment variables")
                return None
        except Exception as e:
            print(f"Error loading API key: {e}")
            return None


# class GeminiAPI:
#     def __init__(self, *args, **kwargs):
#         self.system_prompt = """You are an smart being that like to plan your action"""

#         self.model = "gemini-2.0-flash"  # Using Gemini model


#         # Configure the API key
#         genai.configure(api_key="YOUR_API_KEY")

#         # Use the chat method to interact with the model

#     async def get_response(self, user_input, system_prompt=None):
#         if not system_prompt:
#             system_prompt = self.system_prompt

#         messages=[
#         {'role': 'system', 'content': system_prompt},
#         {'role': 'user', 'content': user_input}
#         ]

#         try:
#             loop = asyncio.get_event_loop()
#             response = await loop.run_in_executor(
#                 None,  # None uses the default executor
#                 lambda: genai.chat(
#                 model=self.model,  # Specify the chat model
#                 messages=messages
#                 ),
#             )
#             response = response['candidates'][0]['content']

#             return response

#         except Exception as e:
#             print(f"Error getting response: {e}")
#             return "I'm having trouble connecting right now."
