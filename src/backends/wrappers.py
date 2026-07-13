"""Composable backend wrappers for fallback, learning, and internet retrieval."""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
import re
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

    @staticmethod
    def _is_backend_failure(exc: Exception) -> bool:
        backend_exceptions = (OSError, TimeoutError, RuntimeError, ValueError)
        if isinstance(exc, backend_exceptions):
            return True

        exc_name = exc.__class__.__name__.lower()
        module_name = exc.__class__.__module__.lower()
        return "openai" in exc_name or "openai" in module_name or "httpx" in module_name

    def generate(self, user_input: str) -> str:
        try:
            return self.primary.generate(user_input)
        except Exception as exc:
            if not self._is_backend_failure(exc):
                raise
            self.logger.warning("Primary backend failed, using fallback: %s", exc)
            return self.secondary.generate(user_input)

    async def agenerate(self, user_input: str) -> str:
        try:
            return await self.primary.agenerate(user_input)
        except Exception as exc:
            if not self._is_backend_failure(exc):
                raise
            self.logger.warning("Primary backend failed, using fallback: %s", exc)
            return await self.secondary.agenerate(user_input)

    def stream_generate(self, user_input: str) -> Iterator[str]:
        try:
            yield from self.primary.stream_generate(user_input)
            return
        except Exception as exc:
            if not self._is_backend_failure(exc):
                raise
            self.logger.warning("Primary stream backend failed, using fallback: %s", exc)
        yield from self.secondary.stream_generate(user_input)

    async def astream_generate(self, user_input: str) -> AsyncIterator[str]:
        try:
            async for chunk in self.primary.astream_generate(user_input):
                yield chunk
            return
        except Exception as exc:
            if not self._is_backend_failure(exc):
                raise
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

    @staticmethod
    def _extract_wikipedia_page_url(data: dict[str, object]) -> str:
        content_urls = data.get("content_urls")
        if not isinstance(content_urls, dict):
            return ""
        desktop = content_urls.get("desktop")
        if not isinstance(desktop, dict):
            return ""
        page = desktop.get("page")
        if not isinstance(page, str):
            return ""
        return page.strip()

    def _build_query_candidates(self, user_input: str) -> list[str]:
        normalized = self._normalize(user_input)
        # Keep only letters/numbers/spaces for retrieval queries.
        cleaned = re.sub(r"[^\w\s]", " ", normalized).strip()
        cleaned = " ".join(cleaned.split())
        if not cleaned:
            return []

        candidates: list[str] = []

        def _add(candidate: str) -> None:
            value = candidate.strip()
            if value and value not in candidates:
                candidates.append(value)

        _add(cleaned)

        # Handle common question-style phrasing.
        shortened = re.sub(
            r"^(what|who|where|when|why|how)\s+(is|are|was|were|do|does|did|can|could|would|should)\s+",
            "",
            cleaned,
        )
        _add(shortened)

        shortened = re.sub(r"^(tell me about|information about|facts about|about)\s+", "", cleaned)
        _add(shortened)

        return candidates

    @staticmethod
    def _is_major_cities_query(user_input: str) -> bool:
        query = user_input.lower()
        has_city_topic = "city" in query or "cities" in query or "capital" in query or "capitals" in query
        is_broad = (
            "major" in query
            or "largest" in query
            or "world" in query
            or "around the world" in query
            or "in the world" in query
        )
        return has_city_topic and is_broad

    @staticmethod
    def _is_capitals_query(user_input: str) -> bool:
        query = user_input.lower()
        return "capital" in query or "capitals" in query

    def _build_city_topic_candidates(self, user_input: str) -> list[str]:
        candidates = self._build_query_candidates(user_input)
        city_terms = {
            "tell",
            "me",
            "please",
            "city",
            "cities",
            "capital",
            "capitals",
            "major",
            "largest",
            "world",
            "great",
            "information",
            "info",
            "about",
        }

        reduced: list[str] = []
        for candidate in candidates:
            tokens = [token for token in candidate.split() if token not in city_terms]
            cleaned = " ".join(tokens).strip()
            if cleaned and cleaned not in reduced and cleaned not in candidates:
                reduced.append(cleaned)

        for item in reduced:
            candidates.append(item)

        return candidates

    def _get_major_cities_overview(self) -> tuple[str, str] | None:
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/Global_city"
        data = self._request_json(summary_url)
        if data is None:
            return None

        extract = str(data.get("extract", "")).strip()
        content_url = self._extract_wikipedia_page_url(data)
        if not extract or not content_url:
            return None
        if not self._is_allowed_source(content_url):
            return None

        curated = (
            "Major examples across regions: Tokyo, Singapore, Seoul, Mumbai (Asia); "
            "Lagos, Cairo, Nairobi, Johannesburg (Africa); "
            "New York City, Mexico City, Sao Paulo, Buenos Aires, Toronto (Americas); "
            "plus London, Paris, Oslo, Stockholm, Copenhagen, and Drammen in Europe.\n"
            "Tip: ask for one city directly, for example: 'Tell me about Drammen'."
        )
        return f"{self._trim_summary(extract)}\n\n{curated}", content_url

    def _get_capitals_overview(self) -> tuple[str, str] | None:
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/Capital_city"
        data = self._request_json(summary_url)
        if data is None:
            return None

        extract = str(data.get("extract", "")).strip()
        content_url = self._extract_wikipedia_page_url(data)
        if not extract or not content_url:
            return None
        if not self._is_allowed_source(content_url):
            return None

        curated = (
            "Major capital examples across regions: Tokyo (Japan), Seoul (South Korea), "
            "Bangkok (Thailand), New Delhi (India) (Asia); "
            "Cairo (Egypt), Abuja (Nigeria), Nairobi (Kenya), Pretoria (South Africa) (Africa); "
            "Washington, D.C. (USA), Mexico City (Mexico), Brasilia (Brazil), Buenos Aires (Argentina) (Americas); "
            "plus Oslo, Stockholm, Copenhagen, London, and Paris in Europe.\n"
            "Tip: ask for one capital directly, for example: 'Tell me about Oslo'."
        )
        return f"{self._trim_summary(extract)}\n\n{curated}", content_url

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

    def _search_wikipedia_titles(self, query: str) -> list[str]:
        safe_query = quote(query)
        search_url = (
            "https://en.wikipedia.org/w/api.php?"
            f"action=opensearch&search={safe_query}&limit=5&namespace=0&format=json"
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
            return []

        if not isinstance(raw, list) or len(raw) < 2:
            return []
        titles = raw[1]
        if not isinstance(titles, list) or not titles:
            return []

        cleaned_titles: list[str] = []
        for title in titles:
            if not isinstance(title, str):
                continue
            normalized = title.strip()
            if normalized and normalized not in cleaned_titles:
                cleaned_titles.append(normalized)
        return cleaned_titles

    def _fetch_wikipedia_summary_with_status(
        self,
        user_input: str,
    ) -> tuple[tuple[str, str] | None, bool, list[str]]:
        if self._is_major_cities_query(user_input):
            if self._is_capitals_query(user_input):
                capitals_overview = self._get_capitals_overview()
                if capitals_overview is not None:
                    return capitals_overview, False, []

            overview = self._get_major_cities_overview()
            if overview is not None:
                return overview, False, []

        queries = self._build_city_topic_candidates(user_input)
        if not queries:
            return None, False, []

        had_lookup_error = False
        suggestion_titles: list[str] = []

        for query in queries:
            candidate_titles: list[str] = [query]
            matched_titles = self._search_wikipedia_titles(query)
            for matched_title in reversed(matched_titles):
                if matched_title != query and matched_title not in candidate_titles:
                    candidate_titles.insert(0, matched_title)

            if len(matched_titles) > 1:
                for title in matched_titles[:3]:
                    if title not in suggestion_titles:
                        suggestion_titles.append(title)

            for title in candidate_titles:
                safe_title = quote(title)
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}"
                data = self._request_json(url)
                if data is None:
                    had_lookup_error = True
                    continue

                extract = str(data.get("extract", "")).strip()
                content_url = self._extract_wikipedia_page_url(data)
                if not extract or not content_url:
                    continue
                if not self._is_allowed_source(content_url):
                    self.logger.info("Rejected source outside allowlist: %s", content_url)
                    return None, False, []

                trimmed = self._trim_summary(extract)
                return (trimmed, content_url), False, suggestion_titles

        return None, had_lookup_error, suggestion_titles

    def _fetch_wikipedia_summary(self, user_input: str) -> tuple[str, str] | None:
        snippet, _, _ = self._fetch_wikipedia_summary_with_status(user_input)
        return snippet

    def _fetch_duckduckgo_summary(self, user_input: str) -> tuple[str, str] | None:
        queries = self._build_query_candidates(user_input)
        if not queries:
            return None

        for query in queries:
            safe_query = quote(query)
            url = (
                "https://api.duckduckgo.com/?"
                f"q={safe_query}&format=json&no_html=1&skip_disambig=1"
            )
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
                continue

            abstract_text = str(data.get("AbstractText", "")).strip()
            abstract_url = str(data.get("AbstractURL", "")).strip()
            if not abstract_text or not abstract_url:
                continue
            if not self._is_allowed_source(abstract_url):
                self.logger.info("Rejected source outside allowlist: %s", abstract_url)
                return None

            return self._trim_summary(abstract_text), abstract_url

        return None

    def _fetch_online_sources(self, user_input: str) -> tuple[list[tuple[str, str]], dict[str, bool | list[str]]]:
        fetchers = {
            "wikipedia": self._fetch_wikipedia_summary,
            "duckduckgo": self._fetch_duckduckgo_summary,
        }
        collected: list[tuple[str, str]] = []
        seen_urls: set[str] = set()
        metadata: dict[str, bool | list[str]] = {
            "wikipedia_lookup_failed": False,
            "wikipedia_suggestions": [],
        }
        for provider in self.source_providers:
            if provider == "wikipedia":
                snippet, had_lookup_error, suggestions = self._fetch_wikipedia_summary_with_status(user_input)
                metadata["wikipedia_lookup_failed"] = bool(metadata["wikipedia_lookup_failed"]) or had_lookup_error
                if suggestions:
                    metadata["wikipedia_suggestions"] = suggestions
            else:
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

        return collected, metadata

    def generate(self, user_input: str) -> str:
        normalized = self._normalize(user_input)
        cached = self.cache.get(normalized)
        if cached is not None and not self._is_stale(cached.get("fetched_at", "")):
            return cached["response"]

        web_answers, metadata = self._fetch_online_sources(user_input)
        if web_answers:
            response = self._format_response_multi(web_answers)
            suggestions = metadata.get("wikipedia_suggestions", [])
            if isinstance(suggestions, list) and len(suggestions) > 1:
                shown = [item for item in suggestions[:3] if isinstance(item, str) and item.strip()]
                if shown:
                    response += "\n\nDid you mean: " + ", ".join(shown) + "?"
            self.cache[normalized] = {
                "response": response,
                "source_url": web_answers[0][1],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_cache()
            return response

        if cached is not None:
            return cached["response"]

        fallback = self.primary.generate(user_input)
        if metadata.get("wikipedia_lookup_failed", False):
            return (
                f"{fallback}\n\n"
                "Note: Wikipedia lookup failed for this query. "
                "Try a more specific search phrase."
            )
        return fallback

    async def agenerate(self, user_input: str) -> str:
        return await asyncio.to_thread(self.generate, user_input)

    def stream_generate(self, user_input: str) -> Iterator[str]:
        yield self.generate(user_input)

    async def astream_generate(self, user_input: str) -> AsyncIterator[str]:
        yield await self.agenerate(user_input)
