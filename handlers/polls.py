import asyncio
import time
from telegram import Update
from telegram.ext import CallbackContext
from config import GALACTUS_CHAT_ID
from utils.cards import CARDS_NAMES, pick_card_without_repetition, get_card_info, format_card_message
from utils.ranking import register_vote
from utils.files import load_active_polls, save_active_polls

VOTE_OPTIONS = ["🏆 Meta", "✅ Boa", "🤔 Situacional", "⚠️ Ruim", "🚫 Injogável"]

_OPTION_TO_SCORE = {0: 2, 1: 1, 2: 0, 3: -1, 4: -2}

def question(card: str) -> str:
    return f'O que você acha da carta "{card}"?'

async def send_single_card_poll(context: CallbackContext):
    chat_id = context.job.data.get("chat_id") if context.job else GALACTUS_CHAT_ID
    if str(chat_id) != str(GALACTUS_CHAT_ID):
        return
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
    
    pergunta = question(carta)

    poll = await context.bot.send_poll(
        chat_id,
        question=pergunta,
        options=VOTE_OPTIONS,
        is_anonymous=False,
        allows_multiple_answers=False,
    )
    context.bot_data.setdefault("active_polls", {})[poll.poll.id] = {
        "carta": carta,
        "chat_id": chat_id,
        "timestamp": int(time.time()),
    }
    save_active_polls(context.bot_data["active_polls"])



async def register_poll_answer(update: Update, context: CallbackContext):
    poll_id = update.poll_answer.poll_id
    poll_data = context.bot_data.get("active_polls", {}).get(poll_id)
    if not poll_data:
        context.bot_data["active_polls"] = load_active_polls()
        poll_data = context.bot_data["active_polls"].get(poll_id)
        if not poll_data:
            return

    idx = update.poll_answer.option_ids[0]
    score = _OPTION_TO_SCORE.get(idx, 0)
    await register_vote(poll_data["carta"], score)
    context.bot_data["active_polls"].pop(poll_id, None)
    save_active_polls(context.bot_data["active_polls"])
