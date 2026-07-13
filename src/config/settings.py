"""Configuration settings for the AI bot."""

from __future__ import annotations

import os

LOG_LEVEL = "INFO"
LOG_FILE = "bot.log"
MAX_WORKERS = 4

DEFAULT_BACKEND = os.getenv("BOT_BACKEND", "rule-based")
ALLOW_BACKEND_FALLBACK = os.getenv("ALLOW_BACKEND_FALLBACK", "1") == "1"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
ENABLE_LEARNING = os.getenv("ENABLE_LEARNING", "1") == "1"
LEARNING_STORE_PATH = os.getenv("LEARNING_STORE_PATH", "data/learned_responses.json")
LEARNING_MIN_SIMILARITY = float(os.getenv("LEARNING_MIN_SIMILARITY", "0.70"))
ENABLE_INTERNET_LEARNING = os.getenv("ENABLE_INTERNET_LEARNING", "0") == "1"
INTERNET_CACHE_PATH = os.getenv("INTERNET_CACHE_PATH", "data/internet_cache.json")
INTERNET_TIMEOUT_SECONDS = int(os.getenv("INTERNET_TIMEOUT_SECONDS", "8"))
INTERNET_MAX_SUMMARY_CHARS = int(os.getenv("INTERNET_MAX_SUMMARY_CHARS", "700"))
SYSTEM_PROMPT_PATH = os.getenv("SYSTEM_PROMPT_PATH", "src/prompts/system_prompt.txt")