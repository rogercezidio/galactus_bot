from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ContextTypes ,CommandHandler
from utils.cards import get_card_info, format_card_message, atualizar_lista_de_cartas
from utils.decks import get_decks_keyboard
from utils.files import load_chat_ids, save_chat_ids, load_last_updated_date
from utils.ranking import calcular_top_bottom, vote_stats, _format_line
from config import SPOTLIGHT_URL, COOLDOWN_TIME, chat_cooldowns, MIN_CARTAS
from utils.snapify import generate_snap_card_with_user_photo 
import random, asyncio
import time
import logging

logger  = logging.getLogger(__name__)
CHANCE  = 0.1 

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


async def spotlight_command(update: Update, context: CallbackContext) -> None:
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
        "Clique abaixo para ver os próximos baús de destaque:",
        reply_markup=reply_markup,
    )


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
        if random.random() < CHANCE:
            try:
                img, cap = await generate_snap_card_with_user_photo(context.bot, message.from_user)
                await context.bot.send_photo(message.chat_id, img, caption=cap, parse_mode="Markdown")
                return
            except Exception as e:
                logger.error("Falha snap-card: %s", e)

        # fallback clássico (sem KeyError!)
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


async def ranking_command(update: Update, context: CallbackContext):
    top, flop, total_cartas = calcular_top_bottom()

    if total_cartas < MIN_CARTAS:
        await update.message.reply_text(
            f"Ainda precisamos de mais variedade!\n"
            f"Atualmente só {total_cartas} cartas receberam votos "
            f"(mínimo {MIN_CARTAS})."
        )
        return

    if not top or not flop:
        await update.message.reply_text("Ainda não há votos suficientes 🤷‍♂️")
        return

    _, total_votos = vote_stats()
    linhas = [
        "*🏆 Ranking das Cartas*",
        f"_Total de votos:_ *{total_votos}*",
        ""
    ]

    linhas.append("🔥 *Top Cards*")
    for pos, (name, media, votos) in enumerate(top, 1):
        linhas.append(_format_line(pos, name, media, votos, flop=False))

    linhas.append("")

    linhas.append("💣 *Bottom Cards*")
    for pos, (name, media, votos) in enumerate(flop, 1):
        linhas.append(_format_line(pos, name, media, votos, flop=True))

    await update.message.reply_text(
        "\n".join(linhas),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    

async def atualizar_lista_de_cartas_command(update: Update, context: CallbackContext):
    try:
        atualizar_lista_de_cartas()
        await update.message.reply_text("✅ Lista de cartas atualizada com sucesso!")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao atualizar cartas: {e}")
