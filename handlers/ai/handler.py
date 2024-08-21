import logging
import json
import asyncio
from time import time as now
from datetime import datetime
import textwrap

import httpx
from decouple import config
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
import cohere

from core.config import ADMIN_ID, ALLOWED_CHATS
from core.bot import app
from handlers.ai.memories import Memories
from handlers.ai.prompts import SYSTEM_PROMPT, RECYCLE_MEMORY_PROMPT


COHERE_API_KEYS_STR = config("COHERE_API_KEYS", default=None)
COHERE_API_KEYS = None

if COHERE_API_KEYS_STR:
    try:
        COHERE_API_KEYS = list(json.loads(COHERE_API_KEYS_STR))
    except Exception as err:
        logging.ERROR(
            "COHERE_API_KEYS has incorrect list structure. Disabling AI module..."
        )

aliases = [
    "саенс",
    "саня",
    "санс",
    "санчес",
    "санчез",
    "александр",
    "фембой",
    "@meet_computer_science_bot",
]
co = None

current_key = 0
chat_history = {}
last_prompt = {}
memory = Memories()


proxy_conf = config("proxy", default=None)
proxies = None
if proxy_conf:
    proxies = {
        'http://': proxy_conf,
        'https://': proxy_conf,
    }


def escape_str(to_escape: str) -> str:
    return to_escape.replace("\\", "\\\\")


async def recycle_memory(depth = 0):
    prompt = RECYCLE_MEMORY_PROMPT.replace("<MEMORIES>", memory.get_all_memories())

    try:
        ai_response = co.chat(
            message=prompt,
            max_tokens=500,
            temperature=0,
            model="command-r-plus",
        )
        new_memories = ai_response.text.split("\n")
        memory.replace_all_memories(new_memories)
    except Exception as err:
        if isinstance(err, cohere.TooManyRequestsError):
            if depth >= len(COHERE_API_KEYS):
                logging.critical("All keys are rate limited.")
                return

            logging.warning("Too many requests. Switching key...")
            update_co()
            await recycle_memory(depth + 1)
            return
        logging.error(err, type(err))


def append_history(chat_id: int, val):
    global chat_history

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    chat_history[chat_id].append(val)

    if len(chat_history[chat_id]) > 5:
        chat_history[chat_id] = chat_history[chat_id][-5:]


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


async def prompt_ai(prompt: str, update: Update, context: ContextTypes.DEFAULT_TYPE, depth: int = 0):
    chat = update.effective_chat
    user = update.effective_user

    if last_prompt.get(chat.id, 0) + 3 > now():
        return

    prompt = escape_str(prompt)

    msg = f"Сообщение от {user.username} - {prompt}"
    logging.info(f"AI prompt - {msg}")
    append_history(chat.id, {"role": "USER", "message": msg})

    current_time = datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S") 

    user_aliases = [name for name in [user.username, user.full_name] if name]
    username = user_aliases[0] # Atleast 1 must be there
    if len(user_aliases) > 1:
        other_aliases = ', '.join(user_aliases[1:])
        username += f" (aka {other_aliases})"

    try:
        preamble = SYSTEM_PROMPT.replace("<MEMORIES>", memory.get_all_memories())

        history = chat_history[chat.id][:-1]

        msg = f"""
        ## Input Text
        {prompt}
        """

        ai_response = co.chat(
            chat_history=history,
            preamble=preamble,
            message=msg,
            max_tokens=200,
            temperature=0,
            model="command-r-plus",
        )

        ai_text: str = ai_response.text
        logging.info(f"AI response: {escape_str(ai_text)}")

        remember_split = ai_text.split("remember")
        if len(remember_split) > 1:
            memory.save_memory(remember_split[1].strip())
            if memory.is_too_much():
                logging.warn("Recycling memory...")
                asyncio.create_task(recycle_memory())

            ai_text = remember_split[0].strip("/")

        if not ai_text:
            logging.info(f"Nothing to answer")
            return

        forget_split = ai_text.split("forget")
        if len(forget_split) > 1:
            memory.delete_memory(forget_split[1].strip())
            ai_text = forget_split[0].strip("/")

        if not ai_text:
            logging.info(f"Nothing to answer")
            return

        append_history(chat.id, {"role": "CHATBOT", "message": escape_str(ai_text)})

        if "<decline>" in ai_text:
            logging.info(f"AI declined.")
            await context.bot.set_message_reaction(
                chat_id=chat.id,
                reaction="👎",
                message_id=update.message.id,
            )
            return

        ai_messages = ai_text.split("\n")
        parts = [textwrap.wrap(m, width=120) for m in ai_messages]
        ai_messages = []
        for p in parts:
            ai_messages.extend(p)

        for i, msg in enumerate(ai_messages):
            if not msg:
                continue
            reply_to = update.message.id if i == 0 else None
            delay = len(msg) / 40

            if i == 0:
                delay -= 5

            last_prompt[chat.id] = now() + delay

            start_time = now()
            while delay > (now() - start_time):
                await context.bot.send_chat_action(chat_id=chat.id, action="typing")
                await asyncio.sleep(0.5)

            await context.bot.send_message(
                chat_id=chat.id,
                text=msg,
                reply_to_message_id=reply_to,
            )
    except Exception as err:
        if isinstance(err, cohere.TooManyRequestsError):
            if depth >= len(COHERE_API_KEYS):
                logging.critical("All keys are rate limited.")
                await context.bot.send_message(chat_id=chat.id, text="Rate limited. Все ключи закончились")
                return

            logging.warning("Too many requests. Switching key...")
            update_co()
            await prompt_ai(prompt, update, context, depth + 1)
            return
        logging.error(err, type(err))
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
    asyncio.create_task(prompt_ai(prompt, update, context))
    

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.id not in ALLOWED_CHATS:
        return

    if not update.message.text or len(update.message.text) < 2:
        return

    if any([(alias in update.message.text.lower()) for alias in aliases]) or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == 7451911720):
        task = prompt_ai(update.message.text, update, context)
        asyncio.create_task(task)
        return

    msg = f"{user.username}: {update.message.text}"
    logging.debug(f"AI history - {msg}")
    append_history(chat.id, {"role": "USER", "message": msg})


if COHERE_API_KEYS:
    update_co()

    app.add_handler(CommandHandler("ai", handle_ai))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
