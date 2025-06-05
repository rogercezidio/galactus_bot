import random
from pathlib import Path
from telegram import Update
from telegram.ext import CallbackContext
from config import GALACTUS_CHAT_ID, GALACTUS_PATTERN, GIF_URL
from utils.api import generate_galactus_roast
from utils.helpers import get_user_profile_photo_async

chat_cooldowns = {}

async def roast_user(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    path = await get_user_profile_photo_async(user.id, context.bot)
    text = await generate_galactus_roast(user.first_name, path)
    await update.message.reply_text(text)
    await context.bot.send_animation(
        chat_id=update.effective_chat.id, animation=GIF_URL
    )

async def daily_curse_by_galactus(update: Update, context: CallbackContext) -> None:
    msg = update.message
    if msg and msg.text and GALACTUS_PATTERN.search(msg.text.lower()):
        chat_id = msg.chat.id
        if str(chat_id) == str(GALACTUS_CHAT_ID):
            if random.random() < 0.15:
                await roast_user(update, context)
            else:
                await msg.reply_text("Banido!")
                await context.bot.send_animation(chat_id=chat_id, animation=GIF_URL)
