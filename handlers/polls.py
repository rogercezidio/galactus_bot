import asyncio
import random
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler
from utils.ranking import calcular_top_bottom, vote_stats
from telegram import Update, Poll
from telegram.ext import (
    CallbackContext,
    PollAnswerHandler,
)
from telegram.ext import CallbackContext
from config import GALACTUS_CHAT_ID
from utils.cards import CARDS_NAMES, pick_card_without_repetition, get_card_info, format_card_message
from utils.ranking import registrar_voto 

VOTE_OPTIONS = ["🏆 Meta", "✅ Boa", "🤔 Situacional", "⚠️ Ruim", "🚫 Injogável"]

_OPTION_TO_SCORE = {0: 2, 1: 1, 2: 0, 3: -1, 4: -2}

def pergunta_com_chat(carta: str, chat_id: int) -> str:
    # Usa um em-dash + último dígito(s) do chat_id. Visualmente é aceitável.
    sufixo = f" —{str(chat_id)[-3:]}"     # ex.: “—123”
    return f'O que você acha da carta "{carta}"?{sufixo}'

async def enviar_enquete_carta_unica(context: CallbackContext):
    chat_id = context.job.data.get("chat_id") if context.job else GALACTUS_CHAT_ID
    carta = pick_card_without_repetition(context.bot_data, CARDS_NAMES)

    loop = asyncio.get_running_loop()
    card_data = await loop.run_in_executor(None, get_card_info, carta)

    if card_data.get("error"):
        await context.bot.send_message(chat_id, card_data["error"])
        return

    caption = format_card_message(card_data)
    if card_data.get("image"):
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=card_data["image"],
            caption=caption,
            parse_mode="Markdown",
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    
    pergunta = pergunta_com_chat(carta, chat_id)

    poll = await context.bot.send_poll(
        chat_id,
        question=pergunta,
        options=VOTE_OPTIONS,
        is_anonymous=False,
        allows_multiple_answers=False,
    )
    context.bot_data.setdefault("active_polls", {})[poll.poll.id] = {"carta": carta}



async def registrar_resposta_enquete(update: Update, context: CallbackContext):
    poll_data = context.bot_data.get("active_polls", {}).get(update.poll_answer.poll_id)
    if not poll_data:
        return

    idx = update.poll_answer.option_ids[0]
    score = _OPTION_TO_SCORE.get(idx, 0)
    await registrar_voto(poll_data["carta"], score)