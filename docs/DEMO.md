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

## 3) Logging Verification

After running either mode, check log output:

```bash
tail -n 20 bot.log
```

## 4) Screenshot Assets

- `docs/screenshots/cli-demo.png`: CLI screenshot placeholder image
- `docs/screenshots/demo-output.txt`: Captured output from `--demo`

To replace `cli-demo.png` with a real screenshot on Linux:

```bash
# Example using gnome-screenshot if available
gnome-screenshot -a -f docs/screenshots/cli-demo.png
```
