"""Backend factory and prompt loading helpers."""

from __future__ import annotations

import logging
from pathlib import Path

from src.backends.base import BackendProtocol
from src.backends.providers import OllamaBackend, OpenAIBackend, RuleBasedBackend
from src.backends.wrappers import FallbackBackend, InternetAugmentedBackend, LearnedBackend


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
    enable_internet_learning: bool,
    internet_cache_path: str,
    internet_timeout_seconds: int,
    internet_max_summary_chars: int,
    internet_cache_ttl_days: int,
    internet_allowed_domains: tuple[str, ...],
    internet_source_providers: tuple[str, ...],
    internet_max_sources: int,
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
        if enable_internet_learning:
            selected = InternetAugmentedBackend(
                primary=selected,
                cache_path=internet_cache_path,
                timeout_seconds=internet_timeout_seconds,
                max_summary_chars=internet_max_summary_chars,
                cache_ttl_days=internet_cache_ttl_days,
                allowed_domains=internet_allowed_domains,
                source_providers=internet_source_providers,
                max_sources=internet_max_sources,
                logger=logger,
            )
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
            if enable_internet_learning:
                selected = InternetAugmentedBackend(
                    primary=selected,
                    cache_path=internet_cache_path,
                    timeout_seconds=internet_timeout_seconds,
                    max_summary_chars=internet_max_summary_chars,
                    cache_ttl_days=internet_cache_ttl_days,
                    allowed_domains=internet_allowed_domains,
                    source_providers=internet_source_providers,
                    max_sources=internet_max_sources,
                    logger=logger,
                )
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

        if enable_internet_learning:
            selected = InternetAugmentedBackend(
                primary=selected,
                cache_path=internet_cache_path,
                timeout_seconds=internet_timeout_seconds,
                max_summary_chars=internet_max_summary_chars,
                cache_ttl_days=internet_cache_ttl_days,
                allowed_domains=internet_allowed_domains,
                source_providers=internet_source_providers,
                max_sources=internet_max_sources,
                logger=logger,
            )

        if enable_learning:
            return LearnedBackend(
                primary=selected,
                learning_store_path=learning_store_path,
                min_similarity=learning_min_similarity,
                logger=logger,
            )
        return selected

    selected = RuleBasedBackend()
    if enable_internet_learning:
        selected = InternetAugmentedBackend(
            primary=selected,
            cache_path=internet_cache_path,
            timeout_seconds=internet_timeout_seconds,
            max_summary_chars=internet_max_summary_chars,
            cache_ttl_days=internet_cache_ttl_days,
            allowed_domains=internet_allowed_domains,
            source_providers=internet_source_providers,
            max_sources=internet_max_sources,
            logger=logger,
        )
    if enable_learning:
        return LearnedBackend(
            primary=selected,
            learning_store_path=learning_store_path,
            min_similarity=learning_min_similarity,
            logger=logger,
        )
    return selected
