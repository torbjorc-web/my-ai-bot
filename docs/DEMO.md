# Demo Guide

This guide shows how to run and present the chatbot demo.

## 1) Interactive Mode

Run:

```bash
python3 -m src.main
```

Example interaction:

```text
You: Hello
Bot: Hello! I am ready to help with your Python AI bot questions.
```

Type `exit` or `quit` to end the chat.

## 2) Concurrent Batch Demo

Run:

```bash
python3 -m src.main --demo
```

This mode processes a set of sample prompts concurrently and prints all responses.

## 3) Asyncio Batch Demo

Run:

```bash
python3 -m src.main --async-demo
```

This mode uses asyncio-based concurrency.

## 4) OpenAI Backend Demo

Install dependencies and set your key:

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your_key"
python3 -m src.main --backend openai --demo
```

## 5) Logging Verification

After running either mode, check log output:

```bash
tail -n 20 bot.log
```

## 6) Screenshot Assets

- `docs/screenshots/cli-demo.png`: CLI screenshot placeholder image
- `docs/screenshots/demo-output.txt`: Captured output from `--demo`
- `docs/screenshots/async-demo-output.txt`: Captured output from `--async-demo`

To replace `cli-demo.png` with a real screenshot on Linux:

```bash
# Example using gnome-screenshot if available
gnome-screenshot -a -f docs/screenshots/cli-demo.png
```
