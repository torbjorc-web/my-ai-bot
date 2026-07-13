"""Shared backend protocols for chatbot backends."""

from __future__ import annotations

from typing import AsyncIterator, Iterator, Protocol, runtime_checkable


class BackendProtocol(Protocol):
    """Behavior contract for all chat backends."""

    def generate(self, user_input: str) -> str:
        ...

    async def agenerate(self, user_input: str) -> str:
        ...

    def stream_generate(self, user_input: str) -> Iterator[str]:
        ...

    def astream_generate(self, user_input: str) -> AsyncIterator[str]:
        ...


@runtime_checkable
class LearningProtocol(Protocol):
    """Optional capability for backends that support user-taught answers."""

    def learn(self, question: str, answer: str) -> None:
        ...
