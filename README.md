# My AI Bot

Python AI chatbot demo project with:

- Structured logging to console and file
- Concurrent message processing using threads
- Asyncio-based concurrent message processing
- Optional real LLM backend with OpenAI
- Token-free local model backend via Ollama
- Streaming responses for supported backends
- Interactive and non-interactive demo modes
- Unit tests and usage documentation

## Features

- `Bot` class with deterministic intent-based responses
- Concurrency via `ThreadPoolExecutor` in batch mode
- Async concurrency via `asyncio` in batch mode
- Optional OpenAI chat backend (`--backend openai`)
- Optional local Ollama backend (`--backend ollama`)
- Automatic fallback chain: OpenAI -> Ollama -> rule-based
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
# PowerShell
.\.venv\Scripts\Activate.ps1

# Git Bash / WSL
source .venv/bin/activate
```

3. Install requirements:

```bash
pip install -r requirements.txt
```

## Run

Interactive chat:

```bash
python -m src.main
```

Concurrent demo mode:

```bash
python -m src.main --demo
```

Async demo mode:

```bash
python -m src.main --async-demo
```

OpenAI backend mode:

```bash
export OPENAI_API_KEY="your_key"
python -m src.main --backend openai --demo
```

PowerShell equivalent:

```powershell
$env:OPENAI_API_KEY = "your_key"
python -m src.main --backend openai --demo
```

Token-free local backend mode:

```bash
# one-time local model setup
ollama pull llama3.1

# run without any API token
python -m src.main --backend ollama --demo
```

Async interactive chat loop:

```bash
python -m src.main --async-chat
```

Streaming in chat mode:

```bash
python -m src.main --backend openai --stream
```

If no backend is provided, the default is `rule-based`.
When `ALLOW_BACKEND_FALLBACK=1`, OpenAI mode will automatically fall back to local Ollama and then rule-based if needed.

Teach the bot new answers at runtime:

```text
/learn how do you feel => I feel great and ready to help.
```

Then ask the same question again and it will use your taught answer. Learned responses are stored in `data/learned_responses.json` by default.
Similar phrasing is also matched with fuzzy similarity (configurable via `LEARNING_MIN_SIMILARITY`).

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