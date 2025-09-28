from openai import OpenAI  # New import
import asyncio
from pathlib import Path
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
from settings import MODEL_PATH, CONTEXT_LENGTH

# import google.generativeai as genai
import time


SYSTEM_PROMPT = """You are an smart being that like to plan your action"""


class LocalAPI:
    def __init__(self):
        model_config = {"max_seq_len": CONTEXT_LENGTH} if CONTEXT_LENGTH else {}

        self.model_path = self._resolve_model_path(MODEL_PATH)
        self.model, self.tokenizer = load(
            self.model_path,
            model_config=model_config,
        )
        self.sampler = make_sampler(temp=0.0)
        self.max_tokens = 256

    def _resolve_model_path(self, configured_path: str) -> str:
        """Resolve the configured model path against common project locations."""

        base_dir = Path(__file__).resolve().parent
        candidates = [
            Path(configured_path),
            base_dir / configured_path,
            base_dir.parent / "model" / configured_path,
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return configured_path

    async def get_response(self, user_input):

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

        try:
            loop = asyncio.get_event_loop()
            current = time.time()

            if hasattr(self.tokenizer, "apply_chat_template"):
                prompt = self.tokenizer.apply_chat_template(
                    messages, add_generation_prompt=True
                )
            else:
                prompt = "\n".join(
                    f"{message['role'].upper()}: {message['content']}" for message in messages
                )

            response = await loop.run_in_executor(
                None,  # None uses the default executor
                lambda: generate(
                    self.model,
                    self.tokenizer,
                    prompt=prompt,
                    sampler=self.sampler,
                    max_tokens=self.max_tokens,
                ),
            )
            ai_response = response.strip()

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
