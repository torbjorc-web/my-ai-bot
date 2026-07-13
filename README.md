# My AI Bot

Python AI chatbot demo project with:

- Structured logging to console and file
- Concurrent message processing using threads
- Asyncio-based concurrent message processing
- Optional real LLM backend with OpenAI
- Token-free local model backend via Ollama
- Optional internet retrieval with local answer cache
- Streaming responses for supported backends
- Typed settings-based backend factory composition
- Interactive and non-interactive demo modes
- Unit tests and usage documentation

## Features

- `Bot` class with deterministic intent-based responses
- Concurrency via `ThreadPoolExecutor` in batch mode
- Async concurrency via `asyncio` in batch mode
- Optional OpenAI chat backend (`--backend openai`)
- Optional local Ollama backend (`--backend ollama`)
- Automatic fallback chain: OpenAI -> Ollama -> rule-based
- Backend assembly via typed settings (`BackendSettings` with provider/learning/internet sub-settings)
- Registry-style backend selection with clear error for unknown backend names
- Optional multi-source web lookup and cached reuse for repeated questions
- Streaming output in interactive and async chat modes (`--stream`)
- Logging configured in one place (`INFO` by default)
- CLI demo switch for fast presentations

## Project Structure

```text
my-ai-bot
├── src
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── providers.py
│   │   └── wrappers.py
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
1. Optional virtualenv:

```bash
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1

# Git Bash / WSL
source .venv/bin/activate
```

1. Install requirements:

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

```powershell
$env:OPENAI_API_KEY = "your_key"
python -m src.main --backend openai --demo
```

Bash equivalent:

```bash
export OPENAI_API_KEY="your_key"
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
When fallback is disabled and OpenAI cannot be initialized, startup fails fast with a clear error.

Teach the bot new answers at runtime:

```text
/learn how do you feel => I feel great and ready to help.
```

Then ask the same question again and it will use your taught answer. Learned responses are stored in `data/learned_responses.json` by default.
Similar phrasing is also matched with fuzzy similarity (configurable via `LEARNING_MIN_SIMILARITY`).

Enable internet retrieval and cache answers locally for next time:

```powershell
$env:ENABLE_INTERNET_LEARNING = "1"
python -m src.main
```

When enabled, the bot will query configured internet providers (default: Wikipedia + DuckDuckGo instant answers) and store successful results in `data/internet_cache.json`.
You can tune behavior with these environment variables:

- `INTERNET_CACHE_PATH` (default `data/internet_cache.json`)
- `INTERNET_TIMEOUT_SECONDS` (default `8`)
- `INTERNET_MAX_SUMMARY_CHARS` (default `700`)
- `INTERNET_CACHE_TTL_DAYS` (default `14`)
- `INTERNET_ALLOWED_DOMAINS` (default `en.wikipedia.org,wikipedia.org,duckduckgo.com`)
- `INTERNET_SOURCE_PROVIDERS` (default `wikipedia,duckduckgo`)
- `INTERNET_MAX_SOURCES` (default `2`)

Responses include a source citation block, and cached answers are refreshed after the TTL expires.

## Logging

- Log level and file are configured in `src/config/settings.py`
- Default log file is `bot.log`
- OpenAI model and temperature are configurable via environment variables

## Backend Composition

- Runtime wiring is built from a typed settings object in `src/main.py` and passed to `create_backend(settings)`.
- The factory composes a base backend (`rule-based`, `ollama`, or `openai`) and then conditionally applies wrappers for internet retrieval and learning.
- Unknown backend names are rejected with a `ValueError` that lists supported backend options.

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Documentation And Screenshots

- Demo guide: `docs/DEMO.md`
- Captured demo transcript: `docs/screenshots/demo-output.txt`
- Captured async transcript: `docs/screenshots/async-demo-output.txt`
