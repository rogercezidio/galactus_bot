import logging
import requests
import re
from bs4 import BeautifulSoup
from telegram.ext import CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import DECK_LIST_URL, UPDATE_FILE_PATH, CHAT_IDS_FILE_PATH
from utils.files import load_last_updated_date, save_last_updated_date, load_chat_ids

logger = logging.getLogger(__name__)


def fetch_updated_date_from_site():
    try:
        response = requests.get(DECK_LIST_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        figcaption_element = soup.find("figcaption")
        if figcaption_element:
            text = figcaption_element.get_text(strip=True)
            # Usa regex para extrair a data após "Updated:"
            match = re.search(r"Updated:\s*(.+)", text)
            if match:
                updated_date_str = match.group(1)
                logger.info(f"Data de atualização encontrada no site: {updated_date_str}")
                return updated_date_str
            else:
                logger.warning("Texto de data não encontrado após 'Updated:' no <figcaption>.")
                return None
        else:
            logger.warning("Elemento <figcaption> com a data de atualização não encontrado no site.")
            return None
    except requests.RequestException as e:
        logger.error(f"Erro ao buscar a página de decks: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao processar a página de decks: {e}")
        return None


def get_decks_keyboard_for_update():
    """
    Cria um teclado inline com um link para a lista de decks.
    Pode ser expandido para mostrar os decks diretamente se desejado.
    """
    keyboard = [[InlineKeyboardButton("Ver Decks Atualizados", url=DECK_LIST_URL)]]
    return InlineKeyboardMarkup(keyboard)


async def check_for_update(context: CallbackContext):
    """
    Verifica se a lista de decks foi atualizada e notifica os chats.
    """
    logger.info("Job 'check_for_update' iniciado.")

    current_site_update_date = fetch_updated_date_from_site()
    last_known_update_date = (
        load_last_updated_date()
    )  # Esta função já está em utils/files

    if current_site_update_date:
        if (
            last_known_update_date is None
            or current_site_update_date != last_known_update_date
        ):
            logger.info(
                f"Nova atualização detectada! Data do site: {current_site_update_date}, Última conhecida: {last_known_update_date}"
            )
            save_last_updated_date(
                current_site_update_date
            )  # Esta função já está em utils/files

            chat_ids_to_notify = load_chat_ids()  # Esta função já está em utils/files
            if not chat_ids_to_notify:
                logger.warning(
                    "Nenhum chat ID encontrado para notificar sobre a atualização."
                )
                return

            message_text = f"📢 O meta do Marvel Snap foi atualizado ({current_site_update_date})!\nConfira os novos decks:"
            reply_markup = get_decks_keyboard_for_update()

            for chat_info in chat_ids_to_notify:
                chat_id = chat_info.get("chat_id")
                if chat_id:
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=message_text,
                            reply_markup=reply_markup,
                        )
                        logger.info(
                            f"Notificação de atualização enviada para o chat ID: {chat_id}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Falha ao enviar notificação de atualização para o chat ID {chat_id}: {e}"
                        )
                else:
                    logger.warning(f"Chat info sem chat_id encontrado: {chat_info}")
        else:
            logger.info(
                f"Nenhuma nova atualização detectada. Data do site ({current_site_update_date}) é a mesma da última conhecida."
            )
    else:
        logger.warning(
            "Não foi possível obter a data de atualização do site. Nenhuma ação tomada."
        )

    logger.info("Job 'check_for_update' finalizado.")
