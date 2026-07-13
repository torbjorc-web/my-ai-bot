# Video Ideas for Coding-Carlsen: My AI Bot

![Content Plan](https://img.shields.io/badge/content-video%20planning-8250DF)
![Series](https://img.shields.io/badge/series-3%20videos-1F6FEB)
![Audience](https://img.shields.io/badge/audience-beginner%20to%20intermediate-0A7EA4)
![Focus](https://img.shields.io/badge/focus-practical%20AI%20engineering-2EA043)

This document includes three different video concepts with practical recording plans.

## Channel Positioning

- Profile: Coding-Carlsen
- Angle: practical AI engineering, not hype
- Style: build in public plus honest debugging and clear takeaways
- Audience: beginner to intermediate Python developers

## Video 1: Build an AI Bot Without API Keys

### Video 1 Goal

Show viewers they can run a useful bot without paid API calls.

### Video 1 Suggested Title

- Build a Python AI Bot With Zero API Keys (Rule-Based + Ollama)

### Video 1 Target Length

- 8 to 12 minutes

### Video 1 Hook

- Most AI bot tutorials start with "get an API key". This one starts with "you do not need one".

### Video 1 Structure

1. Problem setup (0:00 to 1:00)

- Explain API-key friction and cost concerns.

1. Quick architecture tour (1:00 to 2:30)

- Show backend choices and default flow.

1. Live run in no-key mode (2:30 to 5:00)

- Run interactive and demo modes.

1. Optional local model mode (5:00 to 8:00)

- Show the Ollama backend path.

1. Wrap-up and next step (8:00 to 10:00)

- Tease internet retrieval and learning as part two.

### Video 1 Recording Checklist

- Keep terminal font large for mobile viewers.
- Add one simple architecture slide before coding.
- Keep command snippets visible for at least 3 seconds.

### Video 1 CTA

- Comment part 2 if you want internet retrieval and source citations.

## Video 2: Add Safe Internet Learning

### Video 2 Goal

Demonstrate web retrieval done safely with allowlists, citations, and cache refresh.

### Video 2 Suggested Title

- I Added Safe Internet Learning to My Python AI Bot (With Source Citations)

### Video 2 Target Length

- 10 to 15 minutes

### Video 2 Hook

- Connecting a bot to the internet is easy. Doing it safely is the real skill.

### Video 2 Structure

1. Retrieval versus training (0:00 to 1:30)

- Clarify this is not model weight fine-tuning.

1. Feature walkthrough (1:30 to 4:00)

- Show multi-source retrieval, allowlist checks, and TTL cache.

1. Live demo (4:00 to 9:00)

- Ask the same factual question twice and show cache reuse.

1. Safety controls walkthrough (9:00 to 12:00)

- Show environment variables for domains and providers.

1. Trade-offs and limits (12:00 to 14:00)

- Explain stale data and source quality risks.

### Video 2 Recording Checklist

- Prepare three prompts: easy, ambiguous, and blocked-domain.
- Show the cache file briefly and explain the fields.
- Keep one failure demo in the final cut for authenticity.

### Video 2 CTA

- If you want, I can publish source ranking and confidence scoring next.

## Video 3: Refactor a 700+ Line File

### Video 3 Goal

Teach modular architecture by refactoring a real bot file into clear modules.

### Video 3 Suggested Title

- From Spaghetti to Scalable: Refactoring My AI Bot Into Modular Python

### Video 3 Target Length

- 9 to 13 minutes

### Video 3 Hook

- My bot worked, but one file grew to 700+ lines. This refactor fixed that.

### Video 3 Structure

1. Before state and pain points (0:00 to 2:00)

- Show mixed responsibilities in one large file.

1. Refactor plan (2:00 to 3:30)

- Define target module boundaries and why each exists.

1. Step-by-step migration (3:30 to 8:30)

- Move providers, wrappers, and factory code.

1. Validation pass (8:30 to 10:30)

- Run tests and show behavior unchanged.

1. Lessons learned (10:30 to 12:00)

- Explain how to avoid growing monolithic files again.

### Video 3 Recording Checklist

- Show one commit diff for before and after clarity.
- Keep an on-screen checklist while refactoring.
- Include one mistake and fix moment to keep it real.

### Video 3 CTA

- Want a starter repo template with this structure? I can publish one.

## Two-Week Publishing Plan

1. Week 1 Tuesday: Video 1 (no-key bot)
2. Week 1 Friday: Video 2 (safe internet learning)
3. Week 2 Tuesday: Video 3 (modular refactor)

## Short-Form Clips

- Clip A (20 to 35 sec): no API key needed demo.
- Clip B (20 to 40 sec): source citations and allowlist safety.
- Clip C (25 to 45 sec): 700 lines to modular architecture.

## Thumbnail Concepts

- Video 1: NO API KEY text plus terminal screenshot.
- Video 2: SAFE AI BOT text plus lock icon and source list.
- Video 3: 700 LINES TO CLEAN split-screen code view.

## Description Template

Use this structure for each upload:

1. One sentence on what the video teaches.
2. One sentence on why it matters in real projects.
3. Repo link and key commands.
4. One specific question inviting comments.

## Production Tips

- Record in 1080p and increase terminal zoom to 125 to 150 percent.
- Prioritize clean mic audio over visual polish.
- Add chapter timestamps to improve retention.
- End with one focused next-step question.
