"""Rizz HB Bot — Telegram bot that generates pickup/rizz lines
from forwarded conversations using Groq AI.

Buffers forwarded messages, shows a confirmation card with preview
+ inline buttons, and generates only when the user taps Generate.
"""
import asyncio
import logging
import sys

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.config import TELEGRAM_BOT_TOKEN, COOLDOWN_SECONDS
from src.services.groq_service import GroqService

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

# ── session store ─────────────────────────────────────────────
# chat_id -> {"buffer": [{"sender": str|None, "text": str}]}
sessions: dict[int, dict] = {}

DEBOUNCE_S = 1.5    # wait after last message before showing confirm card
TG_LIMIT = 4096

WELCOME = (
    "🤙 *Rizz HB Bot* 🤙\n\n"
    "Forward me a conversation and I'll cook you a smooth pickup line for it.\n\n"
    "*How it works:*\n"
    "1️⃣ Forward one or more messages\n"
    "2️⃣ I'll show what I caught + a ✅ Generate button\n"
    "3️⃣ Tap Generate → I reply with a rizz line\n\n"
    "Commands:\n"
    "/done — generate now (skip the wait)\n"
    "/clear — wipe saved messages\n"
    "/help — more info"
)

HELP = (
    "🤙 *Rizz HB Bot*\n\n"
    "• Forward messages (or paste text) — I'll buffer them\n"
    "• Once you stop sending, I show a preview + buttons\n"
    "• ✅ Generate cooks a line · 🔄 Regenerate rerolls · 🗑 Clear\n\n"
    "Commands: /done · /clear · /help · /model\n\n"
    "*Privacy:* I only see what you explicitly forward to me."
)


def get_session(chat_id: int) -> dict:
    return sessions.setdefault(chat_id, {"buffer": []})


# ── helpers ───────────────────────────────────────────────────


def sender_name(msg) -> str | None:
    """Best-effort original sender name for a forwarded message."""
    fo = getattr(msg, "forward_origin", None)
    if fo is not None:
        su = getattr(fo, "sender_user", None)
        if su is not None:
            return su.full_name
        sc = getattr(fo, "sender_chat", None)
        if sc is not None:
            return sc.title or "Chat"
        ch = getattr(fo, "chat", None)
        if ch is not None:
            return ch.title or "Channel"
    return None


def is_forwarded(msg) -> bool:
    return getattr(msg, "forward_origin", None) is not None


def build_transcript(buffer: list[dict]) -> str:
    lines = []
    for m in buffer:
        if m["sender"]:
            lines.append(f'{m["sender"]}: {m["text"]}')
        else:
            lines.append(m["text"])
    return "\n".join(lines)


def build_preview(buffer: list[dict]) -> str:
    parts = []
    for m in buffer:
        t = m["text"].replace("\n", " ")
        if len(t) > 120:
            t = t[:117] + "..."
        prefix = f'{m["sender"]}: ' if m["sender"] else ""
        parts.append(f"• {prefix}{t}")
    preview = "\n".join(parts)
    if len(preview) > 1500:
        preview = preview[:1500] + "\n…"
    return preview


def split_text(text: str, limit: int = TG_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        cut = text.rfind(" ", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip()
    return chunks


# ── keyboards ─────────────────────────────────────────────────


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Generate", callback_data="gen")],
        [InlineKeyboardButton("➕ Add more", callback_data="add"),
         InlineKeyboardButton("🗑 Clear", callback_data="clr")],
    ])


def result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Regenerate", callback_data="regen"),
         InlineKeyboardButton("🗑 New", callback_data="new")],
    ])


# ── commands ──────────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode="Markdown")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_session(update.effective_chat.id)["buffer"].clear()
    await update.message.reply_text("cleared 🗑️ send a fresh convo whenever 🙏")


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip the debounce and show the confirm card now."""
    chat_id = update.effective_chat.id
    if context.job_queue:
        for job in context.job_queue.get_jobs_by_name(f"confirm_{chat_id}"):
            job.schedule_removal()
    await show_confirm(context.bot, chat_id)


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show or switch the active Groq model."""
    gs = context.bot_data.get("groq_service")
    if not gs:
        await update.message.reply_text("Error: not initialised.")
        return
    current = gs.model
    await update.message.reply_text(
        f"🧠 *Active model:* `{current}`",
        parse_mode="Markdown",
    )


# ── message intake + debounce ─────────────────────────────────


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg is None:
        return
    text = msg.text or msg.caption
    if not text:
        await msg.reply_text("send me text or forwarded messages 🙏 (no media yet)")
        return

    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    session["buffer"].append(
        {"sender": sender_name(msg) if is_forwarded(msg) else None, "text": text}
    )
    schedule_confirm(context, chat_id)


def schedule_confirm(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if context.job_queue is None:
        # JobQueue not available — fire the confirm immediately
        asyncio.create_task(send_confirm_job(context))
        return
    name = f"confirm_{chat_id}"
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    context.job_queue.run_once(send_confirm_job, DEBOUNCE_S, chat_id=chat_id, name=name)


async def send_confirm_job(context: ContextTypes.DEFAULT_TYPE):
    await show_confirm(context.bot, context.job.chat_id)


async def show_confirm(bot, chat_id: int):
    session = get_session(chat_id)
    if not session["buffer"]:
        return
    n = len(session["buffer"])
    preview = build_preview(session["buffer"])
    await bot.send_message(
        chat_id,
        f"got {n} message(s) 📥\n\n{preview}\n\nready for the rizz line? 🤙🔥",
        reply_markup=confirm_keyboard(),
    )


# ── buttons ───────────────────────────────────────────────────


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    chat_id = update.effective_chat.id
    session = get_session(chat_id)

    if data == "add":
        await query.answer()
        await query.edit_message_text("aight, forward/paste more then hit /done 👍")
        return

    if data in ("clr", "new"):
        await query.answer()
        session["buffer"].clear()
        await query.edit_message_text("cleared 🗑️ send a fresh convo whenever 🙏")
        return

    if data in ("gen", "regen"):
        if not session["buffer"]:
            await query.answer("buffer's empty, send a convo first 😅", show_alert=True)
            return
        await query.answer()
        await do_generate(context, query, chat_id, session)


# ── generation ────────────────────────────────────────────────

COOKING_FRAMES = [
    "crafting your rizz line 🤙🔥",
    "smoothness loading... 🥶",
    "consulting the rizz council 🏛️💯",
    "farming aura 📈🗿",
    "calibrating the confidence 🎯",
    "John Pork is on the phone 📞🐷",
    "escaping the friend zone 🌌",
    "unlocking max charisma 🗝️✨",
]
_DOTS = ["", ".", "..", "..."]
ANIM_INTERVAL = 0.8


async def animate(bot, chat_id, message_id, stop: asyncio.Event):
    """Cycle cooking frames on the message until generation finishes."""
    i = 0
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=ANIM_INTERVAL)
            break
        except asyncio.TimeoutError:
            pass
        i += 1
        frame = COOKING_FRAMES[(i // len(_DOTS)) % len(COOKING_FRAMES)]
        text = f"{frame}{_DOTS[i % len(_DOTS)]}"
        try:
            await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id)
        except Exception:
            pass


async def do_generate(context, query, chat_id, session):
    transcript = build_transcript(session["buffer"])
    gs: GroqService = context.bot_data["groq_service"]
    bot = context.bot
    message_id = query.message.message_id

    # Turn the confirm card into a cooking frame
    first_frame = COOKING_FRAMES[0]
    try:
        await query.edit_message_text(first_frame)
    except Exception:
        pass
    await bot.send_chat_action(chat_id, ChatAction.TYPING)

    # Animate while generating
    stop = asyncio.Event()
    anim = asyncio.create_task(animate(bot, chat_id, message_id, stop))
    try:
        line = await gs.generate_rizz(transcript)
    except Exception as e:
        stop.set()
        await anim
        logger.warning("generation failed: %s", e)
        err = f"bro the kitchen exploded 😭🍳💀 ({e})\ntry again with /done"
        try:
            await bot.edit_message_text(err, chat_id=chat_id, message_id=message_id)
        except Exception:
            await bot.send_message(chat_id, err)
        return
    stop.set()
    await anim

    # Replace status with the result
    chunks = split_text(line)
    first_markup = result_keyboard() if len(chunks) == 1 else None
    try:
        await bot.edit_message_text(
            chunks[0], chat_id=chat_id, message_id=message_id, reply_markup=first_markup,
        )
    except Exception:
        await bot.send_message(chat_id, chunks[0], reply_markup=first_markup)
    for i, chunk in enumerate(chunks[1:], start=1):
        markup = result_keyboard() if i == len(chunks) - 1 else None
        await bot.send_message(chat_id, chunk, reply_markup=markup)


# ── entry point ───────────────────────────────────────────────


def main():
    gs = GroqService()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.bot_data["groq_service"] = gs

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler(["clear", "cancel"], cmd_clear))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Rizz HB Bot starting... (model=%s)", gs.model)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
