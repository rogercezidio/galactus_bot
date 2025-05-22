import base64
import logging
import os
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def encode_image(path):
    """Codifica uma imagem em base64."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logging.error(f"Erro ao codificar imagem: {e}")
        return None


def get_user_profile_photo(user_id, bot):
    """Baixa a foto de perfil do usuário e retorna o caminho local."""
    try:
        # Função síncrona para uso em contextos não-async
        photos = bot.get_user_profile_photos(user_id)
        if photos.total_count > 0:
            file = bot.get_file(photos.photos[0][-1].file_id)
            path = os.path.join(Path(__file__).parent, f"{user_id}_photo.jpg")
            file.download_to_drive(path)
            return path
    except Exception as e:
        logging.error(f"Erro ao obter foto de perfil: {e}")
    return None


def get_user_profile_photo_async(user_id, bot):
    """Baixa a foto de perfil do usuário e retorna o caminho local (async)."""
    import asyncio

    async def _get():
        try:
            photos = await bot.get_user_profile_photos(user_id)
            if photos.total_count > 0:
                file = await bot.get_file(photos.photos[0][-1].file_id)
                path = os.path.join(Path(__file__).parent, f"{user_id}_photo.jpg")
                await file.download_to_drive(path)
                return path
        except Exception as e:
            logging.error(f"Erro ao obter foto de perfil (async): {e}")
        return None

    return asyncio.run(_get())


async def send_cosmic_roulette(context, chat_id):
    """
    Envia a mensagem temática da roleta cósmica com link e GIF para o chat especificado.
    """
    link = "https://pay-va.nvsgames.com/topup/262304/"
    gif_url = "https://p19-marketing-va.bytedgame.com/obj/g-marketing-assets-va/2024_07_25_11_34_21/guide_s507015.gif"
    message = (
        "*Mortais insignificantes,*\n"
        "*Vocês estão diante do Devorador de Mundos.* Contemplem a roleta cósmica que está à sua frente! "
        "_O próprio universo treme ao meu comando, e agora, vocês também._ Clique no link, gire a roda do destino "
        "e reivindique os tesouros que apenas o meu poder pode conceder.\n\n"
        "*Não hesitem, pois o tempo é limitado e as recompensas, vastas.* O cosmos não espera pelos fracos. "
        "Clique agora, ou seja esquecido!"
    )
    keyboard = [[InlineKeyboardButton("Girar a roleta cósmica", url=link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_animation(chat_id=chat_id, animation=gif_url)
    await context.bot.send_message(
        chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="Markdown"
    )
