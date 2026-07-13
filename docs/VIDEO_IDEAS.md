# Video Ideas for Coding-Carlsen: My AI Bot

This document gives you three different videos you can publish around this project, each with a concrete plan you can record in one sitting.

## Channel Positioning

- Profile: Coding-Carlsen
- Angle: practical AI engineering, not hype
- Style: build in public + honest debugging + clear takeaways
- Primary audience: beginner to intermediate Python developers

## Video 1: Build an AI Bot Without API Keys

### Goal

Show that people can run a useful AI bot locally without paying for API usage.

### Suggested title

- Build a Python AI Bot With Zero API Keys (Rule-Based + Ollama)

### Target length

- 8 to 12 minutes

### Hook (first 10 seconds)

- "Most AI bot tutorials start with: get an API key. This one starts with: you do not need one."

### Video structure

1. Problem setup (0:00 to 1:00)
- Explain API-key friction and cost concerns.
2. Quick architecture tour (1:00 to 2:30)
- Show backend choices and default flow.
3. Live run: no-key mode (2:30 to 5:00)
- Run interactive and demo modes.
4. Optional local model mode (5:00 to 8:00)
- Show Ollama backend path.
5. Wrap-up and next step (8:00 to 10:00)
- Mention internet retrieval and learning as next episode.

### Recording checklist

- Show terminal commands clearly.
- Keep font size large enough for mobile viewers.
- Add one simple architecture slide before coding.

### CTA

- "Comment 'part 2' if you want internet retrieval and source citations."

## Video 2: Make the Bot Learn Better From the Internet Safely

### Goal

Demonstrate internet retrieval, source allowlists, citations, and cache refresh as a real engineering pattern.

### Suggested title

- I Added Safe Internet Learning to My Python AI Bot (With Source Citations)

### Target length

- 10 to 15 minutes

### Hook (first 10 seconds)

- "It is easy to connect a bot to the internet. It is hard to do it safely. Here is how I did both."

### Video structure

1. Explain retrieval vs model training (0:00 to 1:30)
- Clarify this is not weight fine-tuning.
2. Show feature set (1:30 to 4:00)
- Multi-source retrieval, domain allowlist, TTL cache.
3. Live demo (4:00 to 9:00)
- Ask factual question twice and show cache reuse.
4. Safety controls walkthrough (9:00 to 12:00)
- Show env vars for allowed domains and providers.
5. Trade-offs and limits (12:00 to 14:00)
- Explain stale data and source quality risks.

### Recording checklist

- Prepare 3 prompt examples: easy, ambiguous, and blocked-domain case.
- Show cached file briefly and explain schema.
- Keep one failure demo in the final cut for authenticity.

### CTA

- "If you want, I can open-source a plug-in source ranking module next."

## Video 3: Refactor a 700+ Line Bot File Into Clean Modules

### Goal

Teach practical codebase scaling and refactoring discipline using your real project history.

### Suggested title

- From Spaghetti to Scalable: Refactoring My AI Bot Into Modular Python

### Target length

- 9 to 13 minutes

### Hook (first 10 seconds)

- "My bot worked, but one file grew to 700+ lines. Here is the refactor that saved future me."

### Video structure

1. Before state and pain points (0:00 to 2:00)
- Show large file and mixed responsibilities.
2. Refactor plan (2:00 to 3:30)
- Define target module boundaries.
3. Step-by-step migration (3:30 to 8:30)
- Move providers, wrappers, and factory.
4. Test pass and compatibility check (8:30 to 10:30)
- Run tests and show no behavior change.
5. Lessons learned (10:30 to 12:00)
- How to avoid big-file relapse.

### Recording checklist

- Capture one commit diff for before/after clarity.
- Keep a visible checklist on screen while refactoring.
- Include one "mistake and fix" moment.

### CTA

- "Want a full repo template with this structure? I can publish one next."

## Publishing Plan (2 Weeks)

1. Week 1, Tuesday
- Publish Video 1 (no-key bot).
2. Week 1, Friday
- Publish Video 2 (safe internet learning).
3. Week 2, Tuesday
- Publish Video 3 (refactor architecture).

## Short-Form Cuts You Can Reuse

- Cut A (20 to 35 sec): "No API key needed" quick demo.
- Cut B (20 to 40 sec): "Source citations and allowlist" safety snippet.
- Cut C (25 to 45 sec): "700-line file to modular structure" before/after clip.

## Thumbnail Concepts

- Video 1: "NO API KEY" big text + terminal screenshot.
- Video 2: "SAFE AI BOT" + lock icon + source list visual.
- Video 3: "700 LINES -> CLEAN" + split-screen code view.

## Description Template

Use this for all three videos and customize the middle paragraph:

- What this video teaches in one sentence.
- Why this approach matters in real projects.
- Repo link and key commands.
- Invite viewers to request the next build step.

## Quick Gear + Workflow Suggestions

- Record in 1080p with terminal zoom at 125% to 150%.
- Capture clean mic audio first; viewers forgive video more than bad audio.
- Use chapter timestamps in every upload for retention.
- End each video with one specific next question to drive comments.
