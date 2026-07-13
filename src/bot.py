"""Bot orchestration and compatibility exports for backends."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import AsyncIterator, Iterable, Iterator

from src.backends import (
    BackendSettings,
    BackendProtocol,
    FallbackBackend,
    InternetSettings,
    InternetAugmentedBackend,
    LearnedBackend,
    LearningSettings,
    LearningProtocol,
    OllamaBackend,
    OpenAIBackend,
    ProviderSettings,
    RuleBasedBackend,
    create_backend,
)


@dataclass(slots=True)
class ChatResult:
    """Represents one processed input and its generated response."""

    user_input: str
    response: str


class Bot:
    """Simple AI-like chatbot with deterministic responses and batching support."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        max_workers: int = 4,
        backend: BackendProtocol | None = None,
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

    def stream_response(self, user_input: str) -> Iterator[str]:
        """Stream a response in chunks using the configured backend."""
        self.logger.debug("Streaming input: %s", user_input)
        yield from self.backend.stream_generate(user_input)

    async def stream_response_async(self, user_input: str) -> AsyncIterator[str]:
        """Asynchronously stream a response in chunks using the backend."""
        self.logger.debug("Streaming input asynchronously: %s", user_input)
        async for chunk in self.backend.astream_generate(user_input):
            yield chunk

    def learn(self, question: str, answer: str) -> bool:
        """Teach the bot a new answer if the backend supports learning."""
        learning_backend = self.backend
        if isinstance(learning_backend, LearningProtocol):
            learning_backend.learn(question, answer)
            return True
        return False

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
