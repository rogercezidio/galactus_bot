from telegram import Update
from telegram.ext import ContextTypes
from utils.cards import get_card_info, format_card_message


async def card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.edited_message

    if not message:
        print("Mensagem não encontrada no update.")
        return

    if not context.args:
        await message.reply_text("Use o comando assim: /card [nome da carta]")
        return

    card_name = " ".join(context.args)
    result = get_card_info(card_name)

    if isinstance(result, dict):
        await message.reply_photo(
            photo=result["image"],
            caption=format_card_message(result),
            parse_mode="Markdown",
        )
    else:
        await message.reply_text(result)
