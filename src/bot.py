"""Core chatbot implementation with logging and concurrency support."""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Iterable, Iterator, Protocol, runtime_checkable
from urllib import request


@dataclass(slots=True)
class ChatResult:
    """Represents one processed input and its generated response."""

    user_input: str
    response: str


class BackendProtocol(Protocol):
    """Behavior contract for all chat backends."""

    def generate(self, user_input: str) -> str:
        ...

    async def agenerate(self, user_input: str) -> str:
        ...

    def stream_generate(self, user_input: str) -> Iterator[str]:
        ...

    async def astream_generate(self, user_input: str) -> AsyncIterator[str]:
        ...


@runtime_checkable
class LearningProtocol(Protocol):
    """Optional capability for backends that support user-taught answers."""

    def learn(self, question: str, answer: str) -> None:
        ...


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

    def _post_generate(self, *, prompt: str, stream: bool) -> request.addinfourl:
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
        for chunk in await asyncio.to_thread(lambda: list(self.stream_generate(user_input))):
            yield chunk


class FallbackBackend:
    """Fallback wrapper: use secondary backend if primary fails."""

    def __init__(
        self,
        primary: BackendProtocol,
        secondary: BackendProtocol,
        logger: logging.Logger | None = None,
    ) -> None:
        self.primary = primary
        self.secondary = secondary
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def generate(self, user_input: str) -> str:
        try:
            return self.primary.generate(user_input)
        except Exception as exc:
            self.logger.warning("Primary backend failed, using fallback: %s", exc)
            return self.secondary.generate(user_input)

    async def agenerate(self, user_input: str) -> str:
        try:
            return await self.primary.agenerate(user_input)
        except Exception as exc:
            self.logger.warning("Primary backend failed, using fallback: %s", exc)
            return await self.secondary.agenerate(user_input)

    def stream_generate(self, user_input: str) -> Iterator[str]:
        try:
            yield from self.primary.stream_generate(user_input)
            return
        except Exception as exc:
            self.logger.warning("Primary stream backend failed, using fallback: %s", exc)
        yield from self.secondary.stream_generate(user_input)

    async def astream_generate(self, user_input: str) -> AsyncIterator[str]:
        try:
            async for chunk in self.primary.astream_generate(user_input):
                yield chunk
            return
        except Exception as exc:
            self.logger.warning("Primary stream backend failed, using fallback: %s", exc)
        async for chunk in self.secondary.astream_generate(user_input):
            yield chunk


class LearnedBackend:
    """Persistent Q&A memory wrapper around another backend."""

    def __init__(
        self,
        primary: BackendProtocol,
        learning_store_path: str,
        min_similarity: float,
        logger: logging.Logger | None = None,
    ) -> None:
        self.primary = primary
        self.learning_store_path = learning_store_path
        self.min_similarity = min_similarity
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.learned_map = self._load()

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.strip().lower().split())

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        seq_ratio = difflib.SequenceMatcher(a=a, b=b).ratio()
        a_tokens = set(a.split())
        b_tokens = set(b.split())
        token_overlap = 0.0
        if a_tokens and b_tokens:
            token_overlap = len(a_tokens & b_tokens) / len(a_tokens | b_tokens)
        return max(seq_ratio, token_overlap)

    def _load(self) -> dict[str, str]:
        path = Path(self.learning_store_path)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {self._normalize(k): str(v) for k, v in data.items()}
        except Exception as exc:
            self.logger.warning("Could not load learning store, starting empty: %s", exc)
        return {}

    def _save(self) -> None:
        path = Path(self.learning_store_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.learned_map, indent=2), encoding="utf-8")

    def learn(self, question: str, answer: str) -> None:
        q = self._normalize(question)
        if not q:
            raise ValueError("Question cannot be empty")
        self.learned_map[q] = answer.strip()
        self._save()
        self.logger.info("Learned new response for question pattern: %s", q)

    def _lookup(self, user_input: str) -> str | None:
        normalized = self._normalize(user_input)
        direct = self.learned_map.get(normalized)
        if direct is not None:
            return direct

        best_match = ""
        best_score = 0.0
        for known_question in self.learned_map:
            score = self._similarity(normalized, known_question)
            if score > best_score:
                best_score = score
                best_match = known_question

        if best_match and best_score >= self.min_similarity:
            self.logger.info(
                "Matched learned response using fuzzy similarity %.2f for '%s'",
                best_score,
                best_match,
            )
            return self.learned_map[best_match]
        return None

    def generate(self, user_input: str) -> str:
        learned = self._lookup(user_input)
        if learned is not None:
            return learned
        return self.primary.generate(user_input)

    async def agenerate(self, user_input: str) -> str:
        learned = self._lookup(user_input)
        if learned is not None:
            return learned
        return await self.primary.agenerate(user_input)

    def stream_generate(self, user_input: str) -> Iterator[str]:
        learned = self._lookup(user_input)
        if learned is not None:
            yield learned
            return
        yield from self.primary.stream_generate(user_input)

    async def astream_generate(self, user_input: str) -> AsyncIterator[str]:
        learned = self._lookup(user_input)
        if learned is not None:
            yield learned
            return
        async for chunk in self.primary.astream_generate(user_input):
            yield chunk


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
        if hasattr(self.backend, "learn"):
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
    ollama_host: str,
    ollama_model: str,
    allow_backend_fallback: bool,
    enable_learning: bool,
    learning_store_path: str,
    learning_min_similarity: float,
    system_prompt_path: str,
) -> BackendProtocol:
    """Factory for selecting chatbot backend by name."""
    normalized = backend_name.strip().lower()
    prompt = load_system_prompt(system_prompt_path)
    logger = logging.getLogger("BackendFactory")

    local_chain: BackendProtocol = FallbackBackend(
        primary=OllamaBackend(
            model=ollama_model,
            host=ollama_host,
            system_prompt=prompt,
            temperature=openai_temperature,
        ),
        secondary=RuleBasedBackend(),
        logger=logger,
    )

    if normalized == "ollama":
        selected: BackendProtocol = local_chain
        if enable_learning:
            return LearnedBackend(
                primary=selected,
                learning_store_path=learning_store_path,
                min_similarity=learning_min_similarity,
                logger=logger,
            )
        return selected

    if normalized == "openai":
        try:
            openai_backend = OpenAIBackend(
                api_key=openai_api_key,
                model=openai_model,
                system_prompt=prompt,
                temperature=openai_temperature,
            )
        except Exception:
            if not allow_backend_fallback:
                raise
            logger.warning("OpenAI backend unavailable, using local fallback chain")
            selected = local_chain
            if enable_learning:
                return LearnedBackend(
                    primary=selected,
                    learning_store_path=learning_store_path,
                    min_similarity=learning_min_similarity,
                    logger=logger,
                )
            return selected

        if allow_backend_fallback:
            selected = FallbackBackend(primary=openai_backend, secondary=local_chain, logger=logger)
        else:
            selected = openai_backend

        if enable_learning:
            return LearnedBackend(
                primary=selected,
                learning_store_path=learning_store_path,
                min_similarity=learning_min_similarity,
                logger=logger,
            )
        return selected

    selected = RuleBasedBackend()
    if enable_learning:
        return LearnedBackend(
            primary=selected,
            learning_store_path=learning_store_path,
            min_similarity=learning_min_similarity,
            logger=logger,
        )
    return selected