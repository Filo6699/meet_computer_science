import logging
import json
import importlib
import pkgutil
import asyncio
from random import choice, random
from asyncio import sleep
from typing import Optional

from decouple import config
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import core.logs
from core.config import BOT_TOKEN


app: Optional[Application] = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! There is nothing you can do yet, but you may [contribute](https://github.com/Filo6699/meet_computer_science) or [suggest ideas](https://t.me/wilbursoot_fan)",
        parse_mode="markdown",
    )


def import_all_handlers():
    package = importlib.import_module("handlers")
    package_path = package.__path__

    for _, module_name, _ in pkgutil.iter_modules(package_path):
        logging.info(f"Imported handlers.{module_name}")
        importlib.import_module(f"handlers.{module_name}")


def run_bot():
    global app

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    import_all_handlers()

    app.run_polling(drop_pending_updates=True)
