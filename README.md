# My AI Bot

Python AI chatbot demo project with:

- Structured logging to console and file
- Concurrent message processing using threads
- Asyncio-based concurrent message processing
- Optional real LLM backend with OpenAI
- Streaming responses for supported backends
- Interactive and non-interactive demo modes
- Unit tests and usage documentation

## Features

- `Bot` class with deterministic intent-based responses
- Concurrency via `ThreadPoolExecutor` in batch mode
- Async concurrency via `asyncio` in batch mode
- Optional OpenAI chat backend (`--backend openai`)
- Streaming output in interactive and async chat modes (`--stream`)
- Logging configured in one place (`INFO` by default)
- CLI demo switch for fast presentations

## Project Structure

```
my-ai-bot
├── src
│   ├── bot.py
│   ├── main.py
│   ├── config/
│   │   └── settings.py
│   ├── prompts/
│   │   └── system_prompt.txt
│   └── types/
│       └── __init__.py
├── tests/
│   └── test_bot.py
├── docs/
│   ├── DEMO.md
│   └── screenshots/
│       ├── cli-demo.png
│       └── demo-output.txt
├── requirements.txt
└── README.md
```

## Setup

1. Clone and enter project.
2. Optional virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install requirements:

```bash
pip install -r requirements.txt
```

## Run

Interactive chat:

```bash
python3 -m src.main
```

Concurrent demo mode:

```bash
python3 -m src.main --demo
```

Async demo mode:

```bash
python3 -m src.main --async-demo
```

OpenAI backend mode:

```bash
export OPENAI_API_KEY="your_key"
python3 -m src.main --backend openai --demo
```

Async interactive chat loop:

```bash
python3 -m src.main --async-chat
```

Streaming in chat mode:

```bash
python3 -m src.main --backend openai --stream
```

If no backend is provided, the default is `rule-based`.

## Logging

- Log level and file are configured in `src/config/settings.py`
- Default log file is `bot.log`
- OpenAI model and temperature are configurable via environment variables

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Documentation And Screenshots

- Demo guide: `docs/DEMO.md`
- CLI screenshot: `docs/screenshots/cli-demo.png`
- Captured demo transcript: `docs/screenshots/demo-output.txt`
- Captured async transcript: `docs/screenshots/async-demo-output.txt`