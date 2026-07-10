"""CLI entry point for the chatbot demo."""

from __future__ import annotations

import asyncio
import argparse
import logging

from src.bot import Bot, create_backend
from src.config.settings import (
    DEFAULT_BACKEND,
    LOG_FILE,
    LOG_LEVEL,
    MAX_WORKERS,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    SYSTEM_PROMPT_PATH,
)


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE),
        ],
    )


def run_interactive(bot: Bot) -> None:
    print("Welcome to the AI Bot! Type 'exit' or 'quit' to stop.")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Bot: Goodbye!")
            break
        print(f"Bot: {bot.get_response(user_input)}")


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
        choices=["rule-based", "openai"],
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
        system_prompt_path=SYSTEM_PROMPT_PATH,
    )
    bot = Bot(max_workers=MAX_WORKERS, backend=backend)
    if args.demo:
        run_demo(bot)
        return
    if args.async_demo:
        asyncio.run(run_async_demo(bot))
        return

    run_interactive(bot)


if __name__ == "__main__":
    main()