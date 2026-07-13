"""Composable backend wrappers for fallback, learning, and internet retrieval."""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncIterator, Iterator
from urllib import request
from urllib.parse import quote, urlparse

from src.backends.base import BackendProtocol


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


class InternetAugmentedBackend:
    """Online retrieval wrapper with local cache for repeated questions."""

    def __init__(
        self,
        primary: BackendProtocol,
        cache_path: str,
        timeout_seconds: int,
        max_summary_chars: int,
        cache_ttl_days: int,
        allowed_domains: tuple[str, ...],
        source_providers: tuple[str, ...],
        max_sources: int,
        logger: logging.Logger | None = None,
    ) -> None:
        self.primary = primary
        self.cache_path = cache_path
        self.timeout_seconds = timeout_seconds
        self.max_summary_chars = max_summary_chars
        self.cache_ttl_days = max(cache_ttl_days, 0)
        self.allowed_domains = tuple(
            domain.strip().lower() for domain in allowed_domains if domain.strip()
        )
        self.source_providers = tuple(
            provider.strip().lower()
            for provider in source_providers
            if provider.strip()
        ) or ("wikipedia",)
        self.max_sources = max(1, max_sources)
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.cache = self._load_cache()

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.strip().lower().split())

    def _load_cache(self) -> dict[str, dict[str, str]]:
        path = Path(self.cache_path)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                normalized: dict[str, dict[str, str]] = {}
                for key, value in data.items():
                    normalized_key = self._normalize(str(key))
                    if isinstance(value, str):
                        normalized[normalized_key] = {
                            "response": value,
                            "source_url": "",
                            "fetched_at": datetime.now(timezone.utc).isoformat(),
                        }
                        continue
                    if isinstance(value, dict):
                        response = str(value.get("response", "")).strip()
                        if not response:
                            continue
                        normalized[normalized_key] = {
                            "response": response,
                            "source_url": str(value.get("source_url", "")).strip(),
                            "fetched_at": str(value.get("fetched_at", "")).strip(),
                        }
                return normalized
        except Exception as exc:
            self.logger.warning("Could not load internet cache, starting empty: %s", exc)
        return {}

    def _save_cache(self) -> None:
        path = Path(self.cache_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.cache, indent=2), encoding="utf-8")

    def _is_allowed_source(self, source_url: str) -> bool:
        if not source_url:
            return False
        if not self.allowed_domains:
            return True
        parsed = urlparse(source_url)
        host = (parsed.hostname or "").lower()
        return any(host == domain or host.endswith(f".{domain}") for domain in self.allowed_domains)

    def _is_stale(self, fetched_at: str) -> bool:
        if self.cache_ttl_days == 0:
            return True
        if not fetched_at:
            return True
        try:
            fetched_dt = datetime.fromisoformat(fetched_at)
        except ValueError:
            return True
        if fetched_dt.tzinfo is None:
            fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
        expires_at = fetched_dt + timedelta(days=self.cache_ttl_days)
        return datetime.now(timezone.utc) >= expires_at

    def _format_response_multi(self, summaries: list[tuple[str, str]]) -> str:
        summary_lines = [f"- {summary}" for summary, _ in summaries]
        source_lines = [f"[{idx}] {url}" for idx, (_, url) in enumerate(summaries, start=1)]
        return (
            "I found this online:\n"
            f"{'\n'.join(summary_lines)}\n\n"
            "Sources:\n"
            f"{'\n'.join(source_lines)}"
        )

    def _trim_summary(self, raw_text: str) -> str:
        trimmed = raw_text[: self.max_summary_chars].rstrip()
        if len(raw_text) > self.max_summary_chars:
            trimmed += "..."
        return trimmed

    def _request_json(self, url: str) -> dict[str, object] | None:
        req = request.Request(
            url=url,
            headers={
                "Accept": "application/json",
                "User-Agent": "my-ai-bot/1.0 (internet-learning)",
            },
            method="GET",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self.logger.info("HTTP lookup failed for '%s': %s", url, exc)
            return None

        if isinstance(raw, dict):
            return raw
        return None

    def _search_wikipedia_title(self, query: str) -> str | None:
        safe_query = quote(query)
        search_url = (
            "https://en.wikipedia.org/w/api.php?"
            f"action=opensearch&search={safe_query}&limit=1&namespace=0&format=json"
        )

        req = request.Request(
            url=search_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "my-ai-bot/1.0 (internet-learning)",
            },
            method="GET",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self.logger.info("Wikipedia title search failed for '%s': %s", query, exc)
            return None

        if not isinstance(raw, list) or len(raw) < 2:
            return None
        titles = raw[1]
        if not isinstance(titles, list) or not titles:
            return None
        first_title = titles[0]
        if not isinstance(first_title, str):
            return None
        return first_title.strip() or None

    def _fetch_wikipedia_summary(self, user_input: str) -> tuple[str, str] | None:
        query = self._normalize(user_input)
        if not query:
            return None

        candidate_titles: list[str] = [query]
        matched_title = self._search_wikipedia_title(query)
        if matched_title is not None and matched_title.lower() != query.lower():
            candidate_titles.insert(0, matched_title)

        for title in candidate_titles:
            safe_title = quote(title)
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}"
            data = self._request_json(url)
            if data is None:
                continue

            extract = str(data.get("extract", "")).strip()
            content_url = str(data.get("content_urls", {}).get("desktop", {}).get("page", "")).strip()
            if not extract or not content_url:
                continue
            if not self._is_allowed_source(content_url):
                self.logger.info("Rejected source outside allowlist: %s", content_url)
                return None

            trimmed = self._trim_summary(extract)
            return trimmed, content_url

        return None

    def _fetch_duckduckgo_summary(self, user_input: str) -> tuple[str, str] | None:
        query = self._normalize(user_input)
        if not query:
            return None

        safe_query = quote(query)
        url = f"https://api.duckduckgo.com/?q={safe_query}&format=json&no_html=1&skip_disambig=1"
        req = request.Request(
            url=url,
            headers={
                "Accept": "application/json",
                "User-Agent": "my-ai-bot/1.0 (internet-learning)",
            },
            method="GET",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self.logger.info("DuckDuckGo lookup failed for '%s': %s", query, exc)
            return None

        abstract_text = str(data.get("AbstractText", "")).strip()
        abstract_url = str(data.get("AbstractURL", "")).strip()
        if not abstract_text or not abstract_url:
            return None
        if not self._is_allowed_source(abstract_url):
            self.logger.info("Rejected source outside allowlist: %s", abstract_url)
            return None

        return self._trim_summary(abstract_text), abstract_url

    def _fetch_online_sources(self, user_input: str) -> list[tuple[str, str]]:
        fetchers = {
            "wikipedia": self._fetch_wikipedia_summary,
            "duckduckgo": self._fetch_duckduckgo_summary,
        }
        collected: list[tuple[str, str]] = []
        seen_urls: set[str] = set()
        for provider in self.source_providers:
            fetcher = fetchers.get(provider)
            if fetcher is None:
                self.logger.info("Unknown source provider configured: %s", provider)
                continue

            snippet = fetcher(user_input)
            if snippet is None:
                continue

            summary, source_url = snippet
            if source_url in seen_urls:
                continue
            seen_urls.add(source_url)
            collected.append((summary, source_url))

            if len(collected) >= self.max_sources:
                break

        return collected

    def generate(self, user_input: str) -> str:
        normalized = self._normalize(user_input)
        cached = self.cache.get(normalized)
        if cached is not None and not self._is_stale(cached.get("fetched_at", "")):
            return cached["response"]

        web_answers = self._fetch_online_sources(user_input)
        if web_answers:
            response = self._format_response_multi(web_answers)
            self.cache[normalized] = {
                "response": response,
                "source_url": web_answers[0][1],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_cache()
            return response

        if cached is not None:
            return cached["response"]

        return self.primary.generate(user_input)

    async def agenerate(self, user_input: str) -> str:
        return await asyncio.to_thread(self.generate, user_input)

    def stream_generate(self, user_input: str) -> Iterator[str]:
        yield self.generate(user_input)

    async def astream_generate(self, user_input: str) -> AsyncIterator[str]:
        yield await self.agenerate(user_input)
