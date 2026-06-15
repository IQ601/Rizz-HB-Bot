import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in .env")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE = 0.85
GROQ_MAX_TOKENS = 150
GROQ_TIMEOUT = 20  # seconds

# Bot behavior
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "3"))
ADMIN_USER_IDS = [
    int(uid.strip())
    for uid in os.getenv("ADMIN_USER_IDS", "").split(",")
    if uid.strip()
]

# Prompts
SYSTEM_PROMPT = (
    "You are a witty, creative pickup-line generator. "
    "Given a conversation context, generate an original, smooth, "
    "and contextually-relevant 'rizz' line or pickup line that fits the situation. "
    "Keep it under 2 sentences. Be clever and confident, not creepy or desperate. "
    "If the context is unclear or generic, default to a universally smooth line. "
    "Never use emojis. Reply ONLY with the pickup line — no extra text."
)

FALLBACK_LINES = [
    "Are you made of copper and tellurium? Because you're Cu-Te.",
    "Do you have a map? I keep getting lost in your eyes.",
    "Did it hurt? When you fell from heaven?",
    "Are you a parking ticket? Because you've got FINE written all over you.",
    "Is your name Wi-Fi? Because I'm feeling a connection.",
    "Do you believe in love at first sight, or should I walk by again?",
    "Are you a time traveler? Because I see you in my future.",
    "Your hand looks heavy — here, let me hold it for you.",
    "Are you a magician? Because whenever I look at you, everyone else disappears.",
    "I'm not a photographer, but I can picture us together.",
]
