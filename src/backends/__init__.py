"""Public exports for backend implementations and factory functions."""

from src.backends.base import BackendProtocol, LearningProtocol
from src.backends.factory import create_backend, load_system_prompt
from src.backends.providers import OllamaBackend, OpenAIBackend, RuleBasedBackend
from src.backends.wrappers import FallbackBackend, InternetAugmentedBackend, LearnedBackend

__all__ = [
    "BackendProtocol",
    "LearningProtocol",
    "RuleBasedBackend",
    "OpenAIBackend",
    "OllamaBackend",
    "FallbackBackend",
    "LearnedBackend",
    "InternetAugmentedBackend",
    "create_backend",
    "load_system_prompt",
]
