from telegram import Update
from telegram.ext import CallbackContext
from config import GROUP_RULES, WELCOME_GIF_URL, GIF_URL
from utils.api import generate_galactus_welcome, generate_galactus_farewell


async def welcome_user(update: Update, context: CallbackContext) -> None:
    for user in update.message.new_chat_members:
        name = user.first_name
        msg = await generate_galactus_welcome(name)

        full_msg = f"{msg}\n\nAqui estão as regras do grupo:\n{GROUP_RULES}"
        await context.bot.send_message(update.effective_chat.id, full_msg)
        await context.bot.send_animation(
            update.effective_chat.id, animation=WELCOME_GIF_URL
        )


async def user_left_group(update: Update, context: CallbackContext) -> None:
    name = update.message.left_chat_member.first_name
    msg = await generate_galactus_farewell(name)

    await context.bot.send_message(update.effective_chat.id, msg)
    await context.bot.send_animation(update.effective_chat.id, animation=GIF_URL)
