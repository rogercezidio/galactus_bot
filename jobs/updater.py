import logging
import requests
import re
from bs4 import BeautifulSoup
from telegram.ext import CallbackContext
from utils.decks import get_decks_keyboard
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
            # Tenta pegar o texto do <a> (data)
            a_tag = figcaption_element.find("a")
            if a_tag and a_tag.text.strip():
                updated_date_str = a_tag.text.strip()
                logger.info(f"Data de atualização encontrada no <a>: {updated_date_str}")
                return updated_date_str
            # Fallback: regex no texto do figcaption
            text = figcaption_element.get_text(strip=True)
            match = re.search(r"Updated:\s*(.+)", text)
            if match:
                updated_date_str = match.group(1)
                logger.info(f"Data de atualização encontrada no texto: {updated_date_str}")
                return updated_date_str
            logger.warning("Data não encontrada no <figcaption>.")
            return None
        else:
            logger.warning("Elemento <figcaption> não encontrado.")
            return None
    except requests.RequestException as e:
        logger.error(f"Erro ao buscar a página de decks: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao processar a página de decks: {e}")
        return None

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
            reply_markup = get_decks_keyboard()


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
