import logging
import json
import asyncio

import httpx
from decouple import config
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
import cohere

from core.config import ADMIN_ID, ALLOWED_CHATS
from core.bot import app
from handlers.ai.memories import Memories
from handlers.ai.tools import tools, functions_map, memory
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

proxy_conf = config("proxy", default=None)
proxies = None
if proxy_conf:
    proxies = {
        'http://': proxy_conf,
        'https://': proxy_conf,
    }


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

    httpx_client = None
    if proxies:
        httpx_client = httpx.Client(proxies=proxies)

    co = cohere.Client(
        api_key=key,
        httpx_client=httpx_client,
    )
    logging.warn("Rotating API key for Cohere")


async def prompt_ai(prompt: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    msg = f"{user.username}: {prompt}"
    logging.info(f"AI prompt - {msg}")
    append_history({"role": "USER", "message": msg})

    try:
        formatted_sys = SYSTEM_PROMPT.replace("<MEMORIES>", memory.get_all_memories())
        ai_response = co.chat(
            chat_history=chat_history,
            preamble=formatted_sys,
            message=f"{user.username}: {prompt}",
            max_tokens=400,
            # tools=tools,
            model="command-r-plus",
        )

        # logging.critical(ai_response.tool_calls)
        # if ai_response.tool_calls:
        #     for tool_call in ai_response.tool_calls:
        #         output = functions_map[tool_call.name](**tool_call.parameters)

        ai_text: str = ai_response.text

        if not ai_text:
            logging.info(f"Nothing to answer")
            return

        append_history({"role": "CHATBOT", "message": ai_text})

        if "<decline>" in ai_text:
            logging.info(f"AI declined.")
            await context.bot.set_message_reaction(
                chat_id=chat.id,
                reaction="👎",
                message_id=update.message.id,
            )
            return

        ai_messages = ai_text.split("<break>")

        for i, msg in enumerate(ai_messages):
            if not msg:
                continue
            reply_to = update.message.id if i == 0 else None
            delay = len(msg) / 20

            if i == 0:
                delay -= 3

            if delay > 0:
                await context.bot.send_chat_action(chat_id=chat.id, action="typing")
                await asyncio.sleep(delay)

            await context.bot.send_message(
                chat_id=chat.id,
                text=msg,
                reply_to_message_id=reply_to,
            )
    except Exception as err:
        update_co()
        logging.error(err)
        await context.bot.send_message(chat_id=chat.id, text="Something went wrong.")


async def handle_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await prompt_ai(prompt, update, context)


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

    if "Саенс" in update.message.text or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == 7451911720):
        await prompt_ai(update.message.text, update, context)
        return

    msg = f"{user.username}: {update.message.text}"
    logging.debug(f"AI history - {msg}")
    append_history({"role": "USER", "message": msg})


if COHERE_API_KEYS:
    update_co()

    app.add_handler(CommandHandler("ai", handle_ai))
    app.add_handler(CommandHandler("memory", handle_memories))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
