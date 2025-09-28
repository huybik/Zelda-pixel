import asyncio
import os
import time
from pathlib import Path
from typing import List, Dict, Optional

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
from openai import OpenAI

from .settings import MODEL_PATH, CONTEXT_LENGTH, OBSERVATION_WINDOW

SYSTEM_PROMPT = """You are a concise strategic planner for game NPCs.
Guidelines:
- Only output what is requested (JSON when asked, plain text summary when asked).
- Be deterministic and avoid creativity; prefer short factual reasoning.
- Never invent entities or objects not present in context.
"""

class API:
    """
    Unified API wrapper for both local and OpenAI inference.
    Configured via the 'mode' parameter during initialization.
    """
    _loaded_local_model = False
    _model = None
    _tokenizer = None
    _sampler = None

    def __init__(self, mode: str = "local", max_tokens: int = 192):
        self.mode = mode
        self.max_tokens = max_tokens
        self.system_prompt = SYSTEM_PROMPT

        if self.mode == "local":
            self._initialize_local_model()
        elif self.mode == "openai":
            self.openai_model = "gpt-4o-mini"
            self.client = self._load_openai_api_key()
        else:
            raise ValueError(f"Unsupported API mode: {self.mode}")

    def _initialize_local_model(self):
        """Initializes and caches the local model."""
        if not API._loaded_local_model:
            model_config = {"max_seq_len": CONTEXT_LENGTH} if CONTEXT_LENGTH else {}
            model_path = self._resolve_model_path(MODEL_PATH)
            model, tokenizer = load(model_path, model_config=model_config)
            
            API._model = model
            API._tokenizer = tokenizer
            API._sampler = make_sampler(temp=0.0)
            API._loaded_local_model = True
        
        self.model = API._model
        self.tokenizer = API._tokenizer
        self.sampler = API._sampler

    def _load_openai_api_key(self):
        """Loads the OpenAI API key from environment variables."""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                return OpenAI(api_key=api_key)
            else:
                print("Error: OPENAI_API_KEY not found in environment variables")
                return None
        except Exception as e:
            print(f"Error loading OpenAI API key: {e}")
            return None

    async def get_response(self, user_input: str, system_prompt: Optional[str] = None) -> str:
        """Asynchronously gets a response from the configured AI model."""
        if self.mode == "local":
            return await self._get_local_response(user_input, system_prompt)
        elif self.mode == "openai":
            return await self._get_openai_response(user_input, system_prompt)
        return "ERROR: Invalid mode"

    async def _get_local_response(self, user_input: str, system_prompt: Optional[str]) -> str:
        """Handles local model inference."""
        messages = self._build_messages(user_input, system_prompt)
        try:
            loop = asyncio.get_event_loop()
            started = time.time()
            prompt = self._messages_to_prompt(messages)
            
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

    async def _get_openai_response(self, user_input: str, system_prompt: Optional[str]) -> str:
        """Handles OpenAI model inference."""
        if not self.client:
            return "ERROR: OpenAI client not initialized."
        
        messages = self._build_messages(user_input, system_prompt)
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.openai_model, messages=messages
                ),
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[OpenaiAPI] Error: {e}")
            return "ERROR"

    def _build_messages(self, user_input: str, system_prompt: Optional[str]) -> List[Dict[str, str]]:
        """Builds the message structure for the API call."""
        system_prompt = system_prompt or self.system_prompt
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Converts messages to a string prompt for local models."""
        if hasattr(self.tokenizer, "apply_chat_template"):
            try:
                return self.tokenizer.apply_chat_template(messages, add_generation_prompt=True)
            except Exception:
                pass
        return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages) + "\nASSISTANT:"

    def _resolve_model_path(self, configured_path: str) -> str:
        """Finds the local model path."""
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