"""CLI entry point for the chatbot demo."""

from __future__ import annotations

import argparse
import logging

from src.bot import Bot
from src.config.settings import LOG_FILE, LOG_LEVEL, MAX_WORKERS


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI chatbot")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a non-interactive concurrent demo",
    )
    return parser


def main() -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()

    bot = Bot(max_workers=MAX_WORKERS)
    if args.demo:
        run_demo(bot)
        return

    run_interactive(bot)


if __name__ == "__main__":
    main()