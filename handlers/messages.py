import random
import logging
from utils.api import client
from telegram import Update
from telegram.ext import CallbackContext
from config import GALACTUS_CHAT_ID, GALACTUS_PATTERN, GIF_URL
from handlers.keywords import roast_user


async def galactus_reply(update: Update, context: CallbackContext):
    msg = update.message
    if not msg or not msg.text:
        logging.getLogger(__name__).debug(
            "galactus_reply: Mensagem vazia ou sem texto, retornando."
        )
        return

    chat_id = msg.chat.id
    user_msg = msg.text
    is_reply = (
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id == context.bot.id
    )

    is_mention = any(
        (
            e.type == "mention"
            and f"@{context.bot.username.lower()}"
            in msg.text[e.offset : e.offset + e.length].lower()
        )
        or (e.type == "text_mention" and e.user and e.user.id == context.bot.id)
        for e in msg.entities or []
    )

    if is_reply or is_mention:
        logger = logging.getLogger(__name__)
        try:
            prompt = (
                f"Todo mundo no grupo sabe que você é Galactus, não precisa se apresentar. Imite Galactus em um grupo do Telegram, responda à seguinte mensagem com a personalidade e o tom de Galactus, pode responder com a máxima precisão possível:\nMensagem: {user_message}"
            )

            res = await client.chat.completions.create(
                model="GPT-4.1 mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é Galactus, não precisa se apresentar.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            reply = res.choices[0].message.content
            await context.bot.send_message(chat_id=chat_id, text=reply)
        except Exception as e:
            logger.error(
                f"Erro em galactus_reply ao tentar interagir com a API OpenAI: {e}",
                exc_info=True,
            )
            await msg.reply_text("Galactus está entediado com seus erros humanos...")


async def edited_message_handler(update: Update, context: CallbackContext):
    msg = update.edited_message
    if msg and msg.text and GALACTUS_PATTERN.search(msg.text.lower()):
        chat_id = msg.chat.id
        if str(chat_id) == str(GALACTUS_CHAT_ID):
            if random.random() < 0.25:
                await roast_user(update, context)
            else:
                await msg.reply_text("BANIDO! Tua insolência foi notada por Galactus.")
                await context.bot.send_animation(chat_id=chat_id, animation=GIF_URL)
