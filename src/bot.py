"""Core chatbot implementation with logging and concurrency support."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Iterable


@dataclass(slots=True)
class ChatResult:
    """Represents one processed input and its generated response."""

    user_input: str
    response: str


class Bot:
    """Simple AI-like chatbot with deterministic responses and batching support."""

    def __init__(self, logger: logging.Logger | None = None, max_workers: int = 4) -> None:
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.max_workers = max_workers
        self.logger.debug("Bot initialized with max_workers=%s", max_workers)

    def get_response(self, user_input: str) -> str:
        """Return a response based on basic intent matching."""
        normalized = user_input.strip().lower()
        tokens = normalized.replace("?", " ").replace("!", " ").replace(",", " ").split()
        self.logger.info("Processing input: %s", user_input)

        if not normalized:
            return "Please type a message so I can help you."

        if any(word in tokens for word in ("hello", "hi", "hey")):
            return "Hello! I am ready to help with your Python AI bot questions."

        if any(word in tokens for word in ("bye", "goodbye", "quit", "exit")):
            return "Goodbye! Thanks for chatting."

        if "help" in tokens:
            return "Help: try asking about setup, logging, concurrency, or testing."

        return "I'm not sure how to respond to that yet, but I am learning."

    def process_one(self, user_input: str) -> ChatResult:
        """Process one input and keep a structured result."""
        response = self.get_response(user_input)
        self.logger.debug("Generated response for input: %s", user_input)
        return ChatResult(user_input=user_input, response=response)

    def process_batch_concurrently(self, inputs: Iterable[str]) -> list[ChatResult]:
        """Process many inputs in parallel while preserving input order."""
        input_list = list(inputs)
        self.logger.info("Processing batch concurrently with %s items", len(input_list))
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.process_one, input_list))
        self.logger.info("Finished batch processing")
        return results