"""CLI entry point for the chatbot demo."""

from __future__ import annotations

import asyncio
import argparse
import logging

from src.bot import Bot, create_backend
from src.config.settings import (
    ALLOW_BACKEND_FALLBACK,
    DEFAULT_BACKEND,
    ENABLE_INTERNET_LEARNING,
    ENABLE_LEARNING,
    INTERNET_ALLOWED_DOMAINS,
    INTERNET_CACHE_PATH,
    INTERNET_CACHE_TTL_DAYS,
    INTERNET_MAX_SOURCES,
    INTERNET_MAX_SUMMARY_CHARS,
    INTERNET_SOURCE_PROVIDERS,
    INTERNET_TIMEOUT_SECONDS,
    LEARNING_MIN_SIMILARITY,
    LEARNING_STORE_PATH,
    LOG_FILE,
    LOG_LEVEL,
    MAX_WORKERS,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    SYSTEM_PROMPT_PATH,
)


def _parse_learn_command(user_input: str) -> tuple[str, str] | None:
    if not user_input.startswith("/learn "):
        return None
    payload = user_input[len("/learn "):].strip()
    if "=>" not in payload:
        return None
    question, answer = payload.split("=>", maxsplit=1)
    question = question.strip()
    answer = answer.strip()
    if not question or not answer:
        return None
    return question, answer


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE),
        ],
    )


def run_interactive(bot: Bot, *, stream: bool = False) -> None:
    print("Welcome to the AI Bot! Type 'exit' or 'quit' to stop.")
    print("Tip: teach it with /learn your question => your answer")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Bot: Goodbye!")
            break

        learn_pair = _parse_learn_command(user_input)
        if learn_pair is not None:
            question, answer = learn_pair
            if bot.learn(question, answer):
                print("Bot: Learned. Ask that question again to test it.")
            else:
                print("Bot: Learning is disabled for this backend.")
            continue

        if stream:
            print("Bot: ", end="", flush=True)
            for chunk in bot.stream_response(user_input):
                print(chunk, end="", flush=True)
            print()
            continue

        print(f"Bot: {bot.get_response(user_input)}")


async def run_async_interactive(bot: Bot, *, stream: bool = False) -> None:
    print("Welcome to the async AI Bot! Type 'exit' or 'quit' to stop.")
    print("Tip: teach it with /learn your question => your answer")
    while True:
        user_input = await asyncio.to_thread(input, "You: ")
        user_input = user_input.strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Bot: Goodbye!")
            break

        learn_pair = _parse_learn_command(user_input)
        if learn_pair is not None:
            question, answer = learn_pair
            if bot.learn(question, answer):
                print("Bot: Learned. Ask that question again to test it.")
            else:
                print("Bot: Learning is disabled for this backend.")
            continue

        if stream:
            print("Bot: ", end="", flush=True)
            async for chunk in bot.stream_response_async(user_input):
                print(chunk, end="", flush=True)
            print()
            continue

        response = await bot.get_response_async(user_input)
        print(f"Bot: {response}")


def run_demo(bot: Bot) -> None:
    demo_inputs = [
        "Hello",
        "Can you help me?",
        "What is this?",
        "Goodbye",
    ]
    print("Running concurrent demo with sample inputs...")
    for result in bot.process_batch_concurrently(demo_inputs):
        print(f"You: {result.user_input}")
        print(f"Bot: {result.response}")


async def run_async_demo(bot: Bot) -> None:
    demo_inputs = [
        "Hello",
        "Can you help me?",
        "What is concurrency?",
        "Goodbye",
    ]
    print("Running asyncio demo with sample inputs...")
    results = await bot.process_batch_async(demo_inputs)
    for result in results:
        print(f"You: {result.user_input}")
        print(f"Bot: {result.response}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI chatbot")
    parser.add_argument(
        "--backend",
        choices=["rule-based", "openai", "ollama"],
        default=DEFAULT_BACKEND,
        help="Select response backend",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a non-interactive concurrent demo",
    )
    parser.add_argument(
        "--async-demo",
        action="store_true",
        help="Run a non-interactive asyncio demo",
    )
    parser.add_argument(
        "--async-chat",
        action="store_true",
        help="Run interactive chat loop using asyncio",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream bot output token-by-token when backend supports it",
    )
    return parser


def main() -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    backend = create_backend(
        args.backend,
        openai_api_key=OPENAI_API_KEY,
        openai_model=OPENAI_MODEL,
        openai_temperature=OPENAI_TEMPERATURE,
        ollama_host=OLLAMA_HOST,
        ollama_model=OLLAMA_MODEL,
        allow_backend_fallback=ALLOW_BACKEND_FALLBACK,
        enable_learning=ENABLE_LEARNING,
        learning_store_path=LEARNING_STORE_PATH,
        learning_min_similarity=LEARNING_MIN_SIMILARITY,
        system_prompt_path=SYSTEM_PROMPT_PATH,
        enable_internet_learning=ENABLE_INTERNET_LEARNING,
        internet_cache_path=INTERNET_CACHE_PATH,
        internet_timeout_seconds=INTERNET_TIMEOUT_SECONDS,
        internet_max_summary_chars=INTERNET_MAX_SUMMARY_CHARS,
        internet_cache_ttl_days=INTERNET_CACHE_TTL_DAYS,
        internet_allowed_domains=INTERNET_ALLOWED_DOMAINS,
        internet_source_providers=INTERNET_SOURCE_PROVIDERS,
        internet_max_sources=INTERNET_MAX_SOURCES,
    )
    bot = Bot(max_workers=MAX_WORKERS, backend=backend)
    if args.demo:
        run_demo(bot)
        return
    if args.async_demo:
        asyncio.run(run_async_demo(bot))
        return
    if args.async_chat:
        asyncio.run(run_async_interactive(bot, stream=args.stream))
        return

    run_interactive(bot, stream=args.stream)


if __name__ == "__main__":
    main()