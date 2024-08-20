from random import choice, random
from asyncio import sleep

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from core.config import ALLOWED_CHATS, ADMIN_ID
from core.bot import app


async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.id != ADMIN_ID:
        return

    args = update.message.text.split()

    if len(args) < 3:
        msg = "Usage: /forward <chat_id> message..."
        await context.bot.send_message(chat_id=chat.id, text=msg)
        return

    try:
        forward_chat_id = int(args[1])
    except ValueError as err:
        msg = "Not a valid chat id"
        await context.bot.send_message(chat_id=chat.id, text=msg)
        return

    forward_message = " ".join(args[2:])

    await context.bot.send_message(chat_id=forward_chat_id, text=forward_message)


app.add_handler(CommandHandler("forward", forward))
