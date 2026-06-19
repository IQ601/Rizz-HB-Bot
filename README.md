# Rizz HB Bot 🤙 — [@rizzhbbot](https://t.me/rizzhbbot)

A Telegram bot that generates smooth pickup lines ("rizz") from forwarded conversations using Groq AI.

## How it works

1. **Forward** a conversation (one or more messages) to the bot
2. The bot **buffers** the messages and shows a preview card
3. Tap **✅ Generate** — the bot sends the conversation to Groq AI and replies with a tailored pickup line

## Commands

| Command | What it does |
|---------|-------------|
| `/start` | Welcome + instructions |
| `/done` | Generate now (skip the wait) |
| `/clear` | Wipe saved messages |
| `/help` | More info |

## Quickstart

```bash
# Clone
git clone https://github.com/IQ601/Rizz-HB-Bot.git
cd Rizz-HB-Bot

# Set up
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Mac / Linux

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Fill in your TELEGRAM_BOT_TOKEN and GROQ_API_KEY in .env

# Run
python -m src.bot
```

Or just double-click `run.bat` (Windows).

## Tech

- **Python** 3.10+ / **python-telegram-bot** 20.x
- **Groq** AI (`llama-3.3-70b-versatile`)
- Async polling, animated cooking frames, inline keyboard UI

## Privacy

The bot only sees messages explicitly forwarded to it. No group-wide reading, no data stored long-term.
