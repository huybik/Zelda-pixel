from openai import OpenAI  # New import
import asyncio
from pathlib import Path
from functools import lru_cache
from typing import Iterable, List, Dict, Optional
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
from settings import MODEL_PATH, CONTEXT_LENGTH, OBSERVATION_WINDOW

# import google.generativeai as genai
import time


SYSTEM_PROMPT = """You are a concise strategic planner for game NPCs.
Guidelines:
- Only output what is requested (JSON when asked, plain text summary when asked).
- Be deterministic and avoid creativity; prefer short factual reasoning.
- Never invent entities or objects not present in context.
"""


class LocalAPI:
    """Local inference wrapper with cached model + lightweight prompt tools.

    Features:
    - Singleton model load (subsequent instances reuse the same weights/tokenizer)
    - Deterministic sampling (temp=0.0)
    - Prompt utilities (chat template fallbacks, context trimming)
    - Optional streaming generation (future extensibility)
    """

    # Class-level cache to ensure model only loads once per interpreter
    _loaded = False
    _model = None
    _tokenizer = None
    _sampler = None

    def __init__(self, max_tokens: int = 192):
        if not LocalAPI._loaded:
            model_config = {"max_seq_len": CONTEXT_LENGTH} if CONTEXT_LENGTH else {}
            model_path = self._resolve_model_path(MODEL_PATH)
            model, tokenizer = load(model_path, model_config=model_config)
            sampler = make_sampler(temp=0.0)
            LocalAPI._model = model
            LocalAPI._tokenizer = tokenizer
            LocalAPI._sampler = sampler
            LocalAPI._loaded = True
        self.model = LocalAPI._model
        self.tokenizer = LocalAPI._tokenizer
        self.sampler = LocalAPI._sampler
        self.max_tokens = max_tokens

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

    # ------------------ Prompt Utilities ------------------ #
    def _build_messages(self, user_input: str, system_prompt: Optional[str] = None,
                          extra: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        system_prompt = system_prompt or SYSTEM_PROMPT
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if extra:
            messages.extend(extra)
        messages.append({"role": "user", "content": user_input})
        return messages

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        if hasattr(self.tokenizer, "apply_chat_template"):
            try:
                return self.tokenizer.apply_chat_template(messages, add_generation_prompt=True)
            except Exception:
                pass
        return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages) + "\nASSISTANT:"

    def _truncate_observations(self, observations_json: str, max_items: int = OBSERVATION_WINDOW) -> str:
        """Trim observations array in JSON string by naive slicing (fast + robust enough since upstream builds JSON)."""
        try:
            import json
            data = json.loads(observations_json)
            if isinstance(data, list) and len(data) > max_items:
                data = data[-max_items:]
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            return observations_json  # fallback silently

    async def get_response(self, user_input: str, system_prompt: Optional[str] = None,
                             extra_messages: Optional[List[Dict[str, str]]] = None) -> str:
        messages = self._build_messages(user_input, system_prompt, extra_messages)
        try:
            loop = asyncio.get_event_loop()
            started = time.time()
            prompt = self._messages_to_prompt(messages)
            
            # The blocking generate function is run in an executor to not block the event loop
            raw_text = await loop.run_in_executor(
                None,
                lambda: generate(
                    self.model,
                    self.tokenizer,
                    prompt=prompt,
                    sampler=self.sampler,
                    max_tokens=self.max_tokens,
                ),
            )
            result = raw_text.strip()
            print(f"[LocalAPI] tokens<= {self.max_tokens} | latency={time.time()-started:.2f}s")
            return result
        except Exception as e:
            print(f"[LocalAPI] Error: {e}")
            return "ERROR"


class OpenaiAPI:
    def __init__(self, *args, **kwargs):
        self.system_prompt = SYSTEM_PROMPT
        self.model = "gpt-4o-mini"  # Using GPT-4 Mini model
        self.client = self.load_api_key()

    async def get_response(self, user_input, system_prompt=None):
        if not self.client:
             return "ERROR: OpenAI client not initialized."
        if not system_prompt:
            system_prompt = self.system_prompt

        messages = [
            {"role": "system", "content": system_prompt},
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
            print(f"[OpenaiAPI] Error: {e}")
            return "ERROR"

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
