"""Primary backend provider implementations."""

from __future__ import annotations

import asyncio
import json
import threading
from typing import AsyncIterator, Iterator
from urllib import request
from urllib.response import addinfourl


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

    def stream_generate(self, user_input: str) -> Iterator[str]:
        yield self.generate(user_input)

    async def astream_generate(self, user_input: str) -> AsyncIterator[str]:
        yield self.generate(user_input)


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

    def stream_generate(self, user_input: str) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input},
            ],
            stream=True,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            if content:
                yield content

    async def astream_generate(self, user_input: str) -> AsyncIterator[str]:
        stream = await self.async_client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input},
            ],
            stream=True,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content or ""
            if content:
                yield content


class OllamaBackend:
    """Local Ollama backend over HTTP API, no token required."""

    def __init__(
        self,
        model: str,
        host: str,
        system_prompt: str,
        temperature: float,
        timeout_seconds: int = 60,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    def _post_generate(self, *, prompt: str, stream: bool) -> addinfourl:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": self.system_prompt,
            "stream": stream,
            "options": {"temperature": self.temperature},
        }
        req = request.Request(
            url=f"{self.host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return request.urlopen(req, timeout=self.timeout_seconds)

    def generate(self, user_input: str) -> str:
        with self._post_generate(prompt=user_input, stream=False) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body.get("response", "") or "No response returned."

    async def agenerate(self, user_input: str) -> str:
        return await asyncio.to_thread(self.generate, user_input)

    def stream_generate(self, user_input: str) -> Iterator[str]:
        with self._post_generate(prompt=user_input, stream=True) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                data = json.loads(line)
                chunk = data.get("response", "")
                if chunk:
                    yield chunk

    async def astream_generate(self, user_input: str) -> AsyncIterator[str]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        stream_errors: list[Exception] = []

        def _producer() -> None:
            try:
                for chunk in self.stream_generate(user_input):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop).result()
            except Exception as exc:  # pragma: no cover - exercised via consumer raise
                stream_errors.append(exc)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

        thread = threading.Thread(target=_producer, daemon=True)
        thread.start()

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

        thread.join(timeout=0.1)
        if stream_errors:
            raise stream_errors[0]
