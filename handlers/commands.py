from telegram import Update
from telegram.ext import CallbackContext, ContextTypes
from utils.cards import get_card_info, format_card_message, update_card_list
from utils.decks import get_decks_keyboard
from utils.files import load_chat_ids, save_chat_ids, load_last_updated_date
from config import GALACTUS_CHAT_ID
from utils.snapify import generate_snap_card_with_user_photo 
import random, asyncio
import logging

logger  = logging.getLogger(__name__)
CHANCE  = 0.05

def _is_card_error(res: dict | str) -> bool:
    if isinstance(res, str):
        return True
    if res.get("error"):
        return True
    if res.get("name", "").strip().lower() in {"card not found", "carta não encontrada"}:
        return True
    return False


async def start_command(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    chat_name = update.effective_chat.title or update.effective_chat.first_name
    chats = load_chat_ids()

    if not any(c["chat_id"] == chat_id for c in chats):
        chats.append({"name": chat_name, "chat_id": chat_id})
        save_chat_ids(chats)

    await update.message.reply_text("Olá! Eu sou o Galactus Bot. Estou ouvindo...")


async def decks_command(update: Update, context: CallbackContext) -> None:
    reply_markup = get_decks_keyboard()

    if load_last_updated_date():
        msg = f"Selecione um deck para visualizar:\n\nÚltima atualização: {load_last_updated_date()}"
    else:
        msg = "Selecione um deck para visualizar:\n\nÚltima atualização: Desconhecida"

    if reply_markup:
        await update.message.reply_text(msg, reply_markup=reply_markup)
    else:
        await update.message.reply_text("Falha ao recuperar os decks.")


async def card_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.edited_message
    if not message:
        return

    if not context.args:
        await message.reply_text("Use o comando assim: /card [nome da carta]")
        return

    card_name = " ".join(context.args)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, get_card_info, card_name)

    if _is_card_error(result):
        chat_id = message.chat.id
        if str(chat_id) != str(GALACTUS_CHAT_ID):
            await message.reply_text("Carta não encontrada ou erro na busca.",quote=True)
            return
        if random.random() < CHANCE:

            try:
                img, cap = await generate_snap_card_with_user_photo(context.bot, message.from_user)
                await context.bot.send_photo(message.chat_id, img, caption=cap, parse_mode="Markdown")
                return
            except Exception as e:
                logger.error("Falha snap-card: %s", e)

        msg = result if isinstance(result, str) else result.get("error", "Carta não encontrada.")
        await message.reply_text(msg, quote=True)
        return

    if not result["image"]:
        await message.reply_text(
            format_card_message(result),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        return

    await message.reply_photo(
        photo=result["image"],
        caption=format_card_message(result),
        parse_mode="Markdown",
    )

async def update_card_list_command(update: Update, context: CallbackContext):
    try:
        update_card_list()
        await update.message.reply_text("✅ Lista de cartas atualizada com sucesso!")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao atualizar cartas: {e}")
