# Rizz HB Bot — Implementation Plan

> **Goal:** A Telegram bot that reads conversations from forwarded messages and generates smooth "rizz up" / pickup lines using Groq AI.

---

## 1. Architecture Overview

```
User forwards message(s) in Telegram
         │
         ▼
  Telegram Bot (python-telegram-bot v20.x)
         │
         ├─ Detects forwarded messages
         ├─ Extracts conversation context
         │
         ▼
  Groq AI API (groq Python SDK)
         │
         ├─ Prompt-engineered for pickup lines
         ├─ Model: llama-3.3-70b-versatile (or similar)
         │
         ▼
  Bot replies with generated rizz line
```

**Tech Stack:**
| Component | Library / Tool |
|-----------|---------------|
| Telegram framework | `python-telegram-bot` v20.x (async) |
| AI provider | Groq Cloud API |
| Python SDK | `groq` (~0.9+) |
| Lang/version | Python 3.10+ |
| Dependencies | `python-telegram-bot`, `groq`, `python-dotenv` |

---

## 2. Project Structure

```
C:\Users\Iqbol\Documents\rizz-hb-bot\
├── .env                          # API keys (NOT committed)
├── .gitignore
├── requirements.txt              # Python dependencies
├── PLAN.md                       # This file
├── src/
│   ├── __init__.py
│   ├── bot.py                    # Entry point — runs the bot
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── message_handler.py    # Detects forwards, dispatches to Groq
│   │   └── commands.py           # /start, /help, /model commands
│   ├── services/
│   │   ├── __init__.py
│   │   └── groq_service.py       # Groq API client + prompt construction
│   └── config.py                 # Loads env vars, constants
└── memory/                        # (Claude memory directory — not part of the bot)
```

---

## 3. Core Flow — Step by Step

### 3.1 Detect Forwarded Messages

- Use `Message.forward_date` and `Message.forward_origin` to check if a message is forwarded.
- If `forward_origin` is of type `ForwardOriginChat` or `ForwardOriginUser`, we know it's forwarded.
- **Edge case:** If user sends multiple forwards in a row, collect them as one conversation batch.

### 3.2 Extract Context

- Pull `message.text` or `message.caption` from the forwarded message.
- If no text (photo/video only), reply asking for text context.
- If multiple messages forwarded, concatenate with a separator showing who said what.
- **Edge case:** Empty forwarded message → polite error reply.

### 3.3 Build the Prompt for Groq

**System prompt:**
```
You are a creative, witty pickup-line generator. Given a conversation context,
generate an original, smooth, and contextually-relevant "rizz" line or pickup line
that fits the situation. Keep it under 2 sentences. Be clever, not creepy.
If the context is unclear, default to a universally smooth generic line.
```

**User prompt format:**
```
Conversation context:
"{extracted_text}"

Generate a rizz/pickup line that fits this context:
```

### 3.4 Call Groq API

- Model: `llama-3.3-70b-versatile` (best creative writing, fast on Groq)
- Parameters: `temperature=0.85`, `max_tokens=100`
- Handle rate limits (429) with exponential backoff.

### 3.5 Reply in Telegram

- Reply directly to the forwarded message thread.
- Format with markdown for flair (bold, italics, emojis).
- **Edge case:** If Groq returns empty/refusal, fall back to a curated list of backup lines.

---

## 4. Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message + instructions |
| `/help` | How to use the bot |
| `/model` | Show which Groq model is active |
| `/model <name>` | Switch model (admin-only) |
| `/stats` | Show usage stats (optional, future) |

> **Privacy note:** Forward the conversation, NOT the bot. The bot only reads what's forwarded to it. It **does not** read other group messages.

---

## 5. Setup Instructions

### 5.1 Prerequisites

- Python 3.10+ installed
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Groq API Key (from [console.groq.com](https://console.groq.com))

### 5.2 Quick Start

```bash
# 1. Clone / enter project directory
cd C:\Users\Iqbol\Documents\rizz-hb-bot

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate      # Git Bash / Linux
# OR
venv\Scripts\activate          # cmd.exe

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env
echo "GROQ_API_KEY=your_groq_key_here" >> .env

# 5. Run the bot
python src/bot.py
```

### 5.3 requirements.txt

```
python-telegram-bot==20.8
groq==0.12.0
python-dotenv==1.0.1
```

---

## 6. Prompt Engineering Strategy

The **prompt** is the heart of the bot. We'll iterate:

**V1 — Basic:**
```
Context: "{text}"
Generate a witty pickup line for this situation.
```

**V2 — Structured:**
```
You are "Rizz Master 3000" — an expert at crafting situation-appropriate pickup lines.

Given the conversation context below, create a response that:
1. References something specific from the context
2. Is smooth and confident
3. Makes the recipient smile or laugh
4. Is NOT generic — it must feel tailored

Context: "{text}"

Your pickup line:
```

**V3 — Tone control (optional):**
- Add `tone` parameter: `flirty / funny / smooth / confident / cute`
- User passes it via command: `/rizz funny`

---

## 7. Error Handling Matrix

| Scenario | Behavior |
|----------|----------|
| No forwarded message | Reply: "Forward me a message or conversation to work with!" |
| Empty text content | Reply: "I need some text to work with — try forwarding a message with words!" |
| Groq API timeout | Retry 1x, then reply with a fallback generic rizz line |
| Rate limited (429) | Wait 5s, retry 1x, then apologize + suggest waiting |
| Groq API key invalid | Log error, reply "Bot misconfigured — tell the admin." |
| Unexpected error | Log full trace, reply "Something glitched! Try again?" |

**Fallback lines (when AI fails):**
- "Are you made of copper and tellurium? Because you're Cu-Te."
- "Do you have a map? I keep getting lost in your eyes."
- "Did it hurt? When you fell from heaven?"

---

## 8. Security & Privacy

- **API keys** stored in `.env` (added to `.gitignore`).
- Bot only processes **explicitly forwarded** messages — no group-wide reading.
- Not using `Filters.ALL` — only `Filters.FORWARDED` and command filters.
- Consider adding a **cooldown** per user (e.g., 5 seconds between calls) to prevent abuse.

---

## 9. Development Phases

### Phase 1: Minimal Viable Bot (MVP) ✅
- [x] Basic bot with `/start`
- [x] Detect forwarded messages
- [x] Call Groq with a simple prompt
- [x] Reply with generated line
- [x] `.env` config via `python-dotenv`

### Phase 2: Polish & Edge Cases ✅
- [x] Handle multi-message forwards (caption + text)
- [x] Better error messages (per scenario)
- [x] Fallback lines (10 curated lines)
- [x] Rate limiting / cooldowns (per-user, 3s default)

### Phase 3: Nice-to-Haves ✅
- [x] `/model` command to switch Groq models
- [x] Tone control (API supports it via `generate_rizz(context, tone=)`)
- [x] Admin-only model config (`ADMIN_USER_IDS` in `.env`)
- [x] Forward source display (shows who the message came from)

---

## 10. Bot Status

| Property | Value |
|----------|-------|
| Bot username | @rizzhbbot |
| Telegram token | Configured ✅ |
| Groq API key | Configured ✅ |
| Active model | `llama-3.3-70b-versatile` |
| Groq API test | `"It just got a whole lot better now that I'm talking to you..."` ✅ |
| Process | Running (PID monitored, bot.log active) |

---

## 11. Recommended Groq Models

| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| `llama-3.3-70b-versatile` | Fast | Excellent | **Default** — best overall |
| `llama-3.1-8b-instant` | Very fast | Good | Quick replies, low latency needs |
| `mixtral-8x7b-32768` | Fast | Very good | Longer context / multi-turn |
| `gemma2-9b-it` | Fast | Good | Lighter alternative |

**Default recommendation:** `llama-3.3-70b-versatile` — fast inference on Groq's hardware, great creative text generation.

---

## 12. Next Actions

1. ✅ Plan created
2. ✅ Bot created via [@BotFather](https://t.me/BotFather) — @rizzhbbot
3. ✅ Groq API key configured
4. ✅ Phase 1 & 2 fully implemented
5. 🟡 **Test it now** — Open Telegram and send a forwarded message to @rizzhbbot
6. ☐ Tweak the system prompt in `src/config.py` if the rizz feels off
7. ☐ Deploy (options: Railway, Render, or keep running locally)

---

## 13. File Reference

| File | Purpose |
|------|---------|
| `src/bot.py` | Entry point — wiring, handler registration, `main()` |
| `src/config.py` | All env vars, fallback lines, system prompt |
| `src/handlers/commands.py` | `/start`, `/help`, `/model` commands |
| `src/handlers/message_handler.py` | Forward detection → extract → send typing → reply |
| `src/services/groq_service.py` | Groq API client, prompt construction, error → fallback |
| `.env` | `TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, `GROQ_MODEL`, etc. |
| `bot.log` | Live log file (tail it while testing) |

---

*Built and implemented by Claude Code — Opus 4.8*
