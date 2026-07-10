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
SYSTEM_PROMPT_PATH = os.getenv("SYSTEM_PROMPT_PATH", "src/prompts/system_prompt.txt")