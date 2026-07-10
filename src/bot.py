"""Core chatbot implementation with logging and concurrency support."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class ChatResult:
    """Represents one processed input and its generated response."""

    user_input: str
    response: str


class RuleBasedBackend:
    """Simple deterministic fallback backend."""

    def generate(self, user_input: str) -> str:
        normalized = user_input.strip().lower()
        tokens = normalized.replace("?", " ").replace("!", " ").replace(",", " ").split()

        if not normalized:
            return "Please type a message so I can help you."

        if any(word in tokens for word in ("hello", "hi", "hey")):
            return "Hello! I am ready to help with your Python AI bot questions."

        if any(word in tokens for word in ("bye", "goodbye", "quit", "exit")):
            return "Goodbye! Thanks for chatting."

        if "help" in tokens:
            return "Help: try asking about setup, logging, concurrency, or testing."

        return "I'm not sure how to respond to that yet, but I am learning."

    async def agenerate(self, user_input: str) -> str:
        return self.generate(user_input)


class OpenAIBackend:
    """OpenAI backend using chat completions."""

    def __init__(
        self,
        api_key: str,
        model: str,
        system_prompt: str,
        temperature: float,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI backend")

        try:
            from openai import AsyncOpenAI, OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI backend requested but openai package is not installed"
            ) from exc

        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.client = OpenAI(api_key=api_key)
        self.async_client = AsyncOpenAI(api_key=api_key)

    def generate(self, user_input: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input},
            ],
        )
        return completion.choices[0].message.content or "No response returned."

    async def agenerate(self, user_input: str) -> str:
        completion = await self.async_client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input},
            ],
        )
        return completion.choices[0].message.content or "No response returned."


class Bot:
    """Simple AI-like chatbot with deterministic responses and batching support."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        max_workers: int = 4,
        backend: RuleBasedBackend | OpenAIBackend | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.max_workers = max_workers
        self.backend = backend or RuleBasedBackend()
        self.logger.debug("Bot initialized with max_workers=%s", max_workers)

    def get_response(self, user_input: str) -> str:
        """Return a response using the configured backend."""
        self.logger.info("Processing input: %s", user_input)
        return self.backend.generate(user_input)

    async def get_response_async(self, user_input: str) -> str:
        """Return a response asynchronously using the configured backend."""
        self.logger.info("Processing input asynchronously: %s", user_input)
        return await self.backend.agenerate(user_input)

    def process_one(self, user_input: str) -> ChatResult:
        """Process one input and keep a structured result."""
        response = self.get_response(user_input)
        self.logger.debug("Generated response for input: %s", user_input)
        return ChatResult(user_input=user_input, response=response)

    async def process_one_async(self, user_input: str) -> ChatResult:
        """Asynchronously process one input and keep a structured result."""
        response = await self.get_response_async(user_input)
        self.logger.debug("Generated async response for input: %s", user_input)
        return ChatResult(user_input=user_input, response=response)

    def process_batch_concurrently(self, inputs: Iterable[str]) -> list[ChatResult]:
        """Process many inputs in parallel while preserving input order."""
        input_list = list(inputs)
        self.logger.info("Processing batch concurrently with %s items", len(input_list))
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.process_one, input_list))
        self.logger.info("Finished batch processing")
        return results

    async def process_batch_async(self, inputs: Iterable[str]) -> list[ChatResult]:
        """Process many inputs concurrently with asyncio while preserving order."""
        input_list = list(inputs)
        self.logger.info("Processing async batch with %s items", len(input_list))
        semaphore = asyncio.Semaphore(self.max_workers)

        async def _wrapped(user_input: str) -> ChatResult:
            async with semaphore:
                return await self.process_one_async(user_input)

        results = await asyncio.gather(*(_wrapped(item) for item in input_list))
        self.logger.info("Finished async batch processing")
        return results


def load_system_prompt(prompt_path: str) -> str:
    """Load system prompt from file, fallback to a safe default if missing."""
    path = Path(prompt_path)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return "You are a helpful AI assistant."


def create_backend(
    backend_name: str,
    *,
    openai_api_key: str,
    openai_model: str,
    openai_temperature: float,
    system_prompt_path: str,
) -> RuleBasedBackend | OpenAIBackend:
    """Factory for selecting chatbot backend by name."""
    normalized = backend_name.strip().lower()
    if normalized == "openai":
        return OpenAIBackend(
            api_key=openai_api_key,
            model=openai_model,
            system_prompt=load_system_prompt(system_prompt_path),
            temperature=openai_temperature,
        )
    return RuleBasedBackend()