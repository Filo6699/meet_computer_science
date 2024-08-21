from random import choice, random
from asyncio import sleep

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from handlers.user_join.messages import join_message_groups
from core.config import JOIN_CHATS
from core.bot import app


async def handle_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = None
    user = update.effective_user
    chat = update.effective_chat

    if update.message.new_chat_members:
        pool = join_message_groups

    if pool:
        chat_members = await context.bot.get_chat_member_count(chat.id)
        members_amount = chat_members - 6

        if chat.id not in JOIN_CHATS:
            return

        messages = []
        for msg in pool:
            if random() <= msg["chance"]:
                append_msg: str = choice(msg["messages"])
                fmted = append_msg.format(count=members_amount, user=user.username)
                messages.append(fmted)

        for msg in messages:
            await context.bot.send_message(
                chat_id=chat.id,
                text=msg,
                reply_to_message_id=update.message.id,
            )
            await sleep(1.3)


app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_user))
