from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
import cohere
from decouple import config
import logging
import json
import asyncio

from core.config import ADMIN_ID, ALLOWED_CHATS
from core.bot import app
from handlers.ai.memories import Memories
from handlers.ai.prompts import SYSTEM_PROMPT


COHERE_API_KEYS_STR = config("COHERE_API_KEYS", default=None)
COHERE_API_KEYS = None

if COHERE_API_KEYS_STR:
    try:
        COHERE_API_KEYS = list(json.loads(COHERE_API_KEYS_STR))
    except Exception as err:
        logging.ERROR(
            "COHERE_API_KEYS has incorrect list structure. Disabling AI module..."
        )

co = None
current_key = 0
chat_history = []
memories = Memories()


def append_history(val):
    global chat_history

    chat_history.append(val)
    if len(chat_history) > 10:
        chat_history = chat_history[-25:]


def update_co():
    global current_key, co

    temp = current_key
    current_key = (current_key + 1) % len(COHERE_API_KEYS)
    key = COHERE_API_KEYS[temp]

    co = cohere.Client(
        api_key=key,
    )
    logging.warn("Rotating API key for Cohere")


async def prompt_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.id not in ALLOWED_CHATS:
        return

    args = update.message.text.split()

    if len(args) < 2:
        msg = "Usage: /ai message..."
        await context.bot.send_message(chat_id=chat.id, text=msg)
        return

    prompt = " ".join(args[1:])
    msg = f"{user.username}: {prompt}"
    logging.info(f"AI prompt - {msg}")
    append_history({"role": "USER", "message": msg})
    
    try:
        formatted_sys = SYSTEM_PROMPT.replace("<MEMORIES>", memories.get_all_memories())
        ai_response = co.chat(
            chat_history=chat_history,
            preamble=formatted_sys,
            message=f"{user.username}: {prompt}",
            max_tokens=250,
            model="command-r-plus",
        )

        ai_text: str = ai_response.text
        append_history({"role": "CHATBOT", "message": ai_text})
        remember_split = ai_text.split("/remember")
        
        if len(remember_split) > 1:
            ai_text = remember_split[0].strip()
            for remb_chunk in remember_split[1:]:
                args = remb_chunk.split(" ")
                if len(args) < 3:
                    continue
                memories.save_memory(args[1], " ".join(args[2:]))

        if not ai_text:
            logging.info(f"Nothing to answer")
            return

        if "<decline>" in ai_text:
            logging.info(f"AI declined.")
            await context.bot.set_message_reaction(
                chat_id=chat.id,
                reaction="👎",
                message_id=update.message.id,
            )
            return

        ai_messages = ai_text.split("<break>")

        await context.bot.send_chat_action(chat_id=chat.id, action='typing')

        for i, msg in enumerate(ai_messages):
            if not msg:
                continue
            reply_to = update.message.id if i == 0 else None
            delay = len(msg) / 12

            if i == 0:
                delay -= 3

            if delay > 0:
                await asyncio.sleep(delay)

            await context.bot.send_message(
                chat_id=chat.id,
                text=msg,
                reply_to_message_id=reply_to,
            )
    except Exception as err:
        update_co()
        err_msg = f"Failed to send AI prompt: {ai_response}"
        logging.error(err_msg)
        logging.error(err.args)
        await context.bot.send_message(chat_id=chat.id, text="Something went wrong.")


async def handle_memories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.username
    chat = update.effective_chat

    args = update.message.text.split()
    if len(args) > 2:
        await context.bot.send_message(chat_id=chat.id, text=memory)
    
    memory = memories.get_memory(user)
    await context.bot.send_message(chat_id=chat.id, text=memory)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.id not in ALLOWED_CHATS:
        return

    if not update.message.text or len(update.message.text) < 2:
        return

    msg = f"{user.username}: {update.message.text}"
    logging.debug(f"AI history - {msg}")
    append_history({"role": "USER", "message": msg})


if COHERE_API_KEYS:
    update_co()

    app.add_handler(CommandHandler("ai", prompt_ai))
    app.add_handler(CommandHandler("memory", handle_memories))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
