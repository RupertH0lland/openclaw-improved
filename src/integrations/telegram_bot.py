"""Telegram bot integration - chat with orchestrator via Telegram."""
import asyncio
import os
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from src.config import load_config, get_env
from src.orchestrator.core import Orchestrator


def run_telegram_bot(project_root: Path) -> None:
    """Run the Telegram bot (blocking)."""
    settings, _ = load_config(project_root)
    env = get_env(project_root)
    if not settings.telegram.enabled and not env.telegram_bot_token:
        return
    token = settings.telegram.bot_token or env.telegram_bot_token
    if not token:
        return

    orchestrator = Orchestrator(project_root)

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return
        user_msg = update.message.text
        chat_id = update.effective_chat.id if update.effective_chat else None
        if not chat_id:
            return
        full_response = ""
        async for token in orchestrator.process(user_msg, source="telegram", stream=True):
            full_response += token
        await update.message.reply_text(full_response or "(No response)")

    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "AI Orchestrator bot. Send a message to chat with the orchestrator. "
            "Commands: /task /cron /status /memory /config"
        )

    async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Orchestrator is running.")

    def main() -> None:
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("status", cmd_status))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.run_polling()

    main()
