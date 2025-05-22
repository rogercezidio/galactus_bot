import os
import json
from config import CHAT_IDS_FILE_PATH, UPDATE_FILE_PATH, logger

last_updated_date = None


def load_chat_ids():
    if not os.path.exists(CHAT_IDS_FILE_PATH):
        logger.warning(f"Arquivo de chat_ids não encontrado: {CHAT_IDS_FILE_PATH}")
        return []
    try:
        with open(CHAT_IDS_FILE_PATH, "r") as f:
            data = json.load(f)
            return data.get("chats", [])
    except Exception as e:
        logger.error(f"Erro ao carregar chat_ids: {e}")
        return []


def save_chat_ids(chat_ids):
    try:
        with open(CHAT_IDS_FILE_PATH, "w") as f:
            json.dump({"chats": chat_ids}, f, indent=4)
        logger.info(f"{len(chat_ids)} chat_id(s) salvos.")
    except Exception as e:
        logger.error(f"Erro ao salvar chat_ids: {e}")


def load_last_updated_date():
    global last_updated_date
    if os.path.exists(UPDATE_FILE_PATH):
        try:
            with open(UPDATE_FILE_PATH, "r") as f:
                last_updated_date = f.read().strip()
                logger.info(
                    f"Data de última atualização carregada: {last_updated_date}"
                )
        except Exception as e:
            logger.error(f"Erro ao carregar data de atualização: {e}")


def save_last_updated_date(date):
    global last_updated_date
    try:
        with open(UPDATE_FILE_PATH, "w") as f:
            f.write(date)
            last_updated_date = date
            logger.info(f"Data de atualização salva: {last_updated_date}")
    except Exception as e:
        logger.error(f"Erro ao salvar data de atualização: {e}")
