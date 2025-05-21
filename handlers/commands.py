from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from utils.decks import get_decks_keyboard
from utils.files import load_chat_ids, save_chat_ids, last_updated_date
from config import SPOTLIGHT_URL, COOLDOWN_TIME, chat_cooldowns
import time

async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    chat_name = update.effective_chat.title or update.effective_chat.first_name
    chats = load_chat_ids()

    if not any(c['chat_id'] == chat_id for c in chats):
        chats.append({"name": chat_name, "chat_id": chat_id})
        save_chat_ids(chats)

    await update.message.reply_text('Olá! Eu sou o Galactus Bot. Estou ouvindo...')

async def decks(update: Update, context: CallbackContext) -> None:
    reply_markup = get_decks_keyboard()

    if last_updated_date:
        msg = f"Selecione um deck para visualizar:\n\nÚltima atualização: {last_updated_date}"
    else:
        msg = "Selecione um deck para visualizar:\n\nÚltima atualização: Desconhecida"

    if reply_markup:
        await update.message.reply_text(msg, reply_markup=reply_markup)
    else:
        await update.message.reply_text('Falha ao recuperar os decks.')

async def spotlight(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    now = time.time()

    if chat_id in chat_cooldowns:
        elapsed = now - chat_cooldowns[chat_id]
        if elapsed < COOLDOWN_TIME:
            return  # cooldown ativo

    chat_cooldowns[chat_id] = now
    keyboard = [[InlineKeyboardButton("Baús de Destaque", url=SPOTLIGHT_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Clique abaixo para ver os próximos baús de destaque:", reply_markup=reply_markup
    )
