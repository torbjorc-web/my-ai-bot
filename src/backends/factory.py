"""Backend factory and prompt loading helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.backends.base import BackendProtocol
from src.backends.providers import OllamaBackend, OpenAIBackend, RuleBasedBackend
from src.backends.wrappers import FallbackBackend, InternetAugmentedBackend, LearnedBackend


@dataclass(frozen=True, slots=True)
class ProviderSettings:
    """Provider-specific model and credential settings."""

    openai_api_key: str
    openai_model: str
    openai_temperature: float
    ollama_host: str
    ollama_model: str


@dataclass(frozen=True, slots=True)
class LearningSettings:
    """Settings for local learning persistence and match behavior."""

    enabled: bool
    store_path: str
    min_similarity: float


@dataclass(frozen=True, slots=True)
class InternetSettings:
    """Settings for optional internet retrieval and caching."""

    enabled: bool
    cache_path: str
    timeout_seconds: int
    max_summary_chars: int
    cache_ttl_days: int
    allowed_domains: tuple[str, ...]
    source_providers: tuple[str, ...]
    max_sources: int


@dataclass(frozen=True, slots=True)
class BackendSettings:
    """Top-level backend wiring policy and sub-configuration."""

    backend_name: str
    allow_backend_fallback: bool
    system_prompt_path: str
    providers: ProviderSettings
    learning: LearningSettings
    internet: InternetSettings


def load_system_prompt(prompt_path: str) -> str:
    """Load system prompt from file, fallback to a safe default if missing."""
    path = Path(prompt_path)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return "You are a helpful AI assistant."


def _build_local_chain(settings: BackendSettings, prompt: str, logger: logging.Logger) -> BackendProtocol:
    return FallbackBackend(
        primary=OllamaBackend(
            model=settings.providers.ollama_model,
            host=settings.providers.ollama_host,
            system_prompt=prompt,
            temperature=settings.providers.openai_temperature,
        ),
        secondary=RuleBasedBackend(),
        logger=logger,
    )


def _apply_optional_wrappers(
    base: BackendProtocol,
    *,
    settings: BackendSettings,
    logger: logging.Logger,
) -> BackendProtocol:
    selected = base
    if settings.internet.enabled:
        selected = InternetAugmentedBackend(
            primary=selected,
            cache_path=settings.internet.cache_path,
            timeout_seconds=settings.internet.timeout_seconds,
            max_summary_chars=settings.internet.max_summary_chars,
            cache_ttl_days=settings.internet.cache_ttl_days,
            allowed_domains=settings.internet.allowed_domains,
            source_providers=settings.internet.source_providers,
            max_sources=settings.internet.max_sources,
            logger=logger,
        )

    if settings.learning.enabled:
        selected = LearnedBackend(
            primary=selected,
            learning_store_path=settings.learning.store_path,
            min_similarity=settings.learning.min_similarity,
            logger=logger,
        )
    return selected


def _build_ollama_backend(settings: BackendSettings, prompt: str, logger: logging.Logger) -> BackendProtocol:
    return _build_local_chain(settings, prompt, logger)


def _build_openai_backend(settings: BackendSettings, prompt: str, logger: logging.Logger) -> BackendProtocol:
    local_chain = _build_local_chain(settings, prompt, logger)
    try:
        openai_backend = OpenAIBackend(
            api_key=settings.providers.openai_api_key,
            model=settings.providers.openai_model,
            system_prompt=prompt,
            temperature=settings.providers.openai_temperature,
        )
    except (RuntimeError, ValueError) as exc:
        if not settings.allow_backend_fallback:
            raise
        logger.warning(
            "OpenAI backend construction failed (%s), using local fallback chain",
            exc,
        )
        return local_chain

    if settings.allow_backend_fallback:
        logger.info("Backend fallback enabled: wrapping OpenAI with local secondary chain")
        return FallbackBackend(primary=openai_backend, secondary=local_chain, logger=logger)
    return openai_backend


def _build_rule_based_backend(settings: BackendSettings, prompt: str, logger: logging.Logger) -> BackendProtocol:
    del settings, prompt, logger
    return RuleBasedBackend()


def create_backend(settings: BackendSettings) -> BackendProtocol:
    """Factory for selecting and composing chatbot backends from typed settings."""
    normalized = settings.backend_name.strip().lower()
    prompt = load_system_prompt(settings.system_prompt_path)
    logger = logging.getLogger("BackendFactory")
    builders = {
        "ollama": _build_ollama_backend,
        "openai": _build_openai_backend,
        "rule-based": _build_rule_based_backend,
    }

    if normalized not in builders:
        supported = ", ".join(sorted(builders))
        raise ValueError(f"Unknown backend '{settings.backend_name}'. Supported backends: {supported}")

    base_backend = builders[normalized](settings, prompt, logger)
    return _apply_optional_wrappers(base_backend, settings=settings, logger=logger)
