import os
import json
from config import CHAT_IDS_FILE_PATH, UPDATE_FILE_PATH, CARDS_SENT_FILE, logger

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
        
        return last_updated_date

def save_last_updated_date(date):
    global last_updated_date
    try:
        with open(UPDATE_FILE_PATH, "w") as f:
            f.write(date)
            last_updated_date = date
            logger.info(f"Data de atualização salva: {last_updated_date}")
    except Exception as e:
        logger.error(f"Erro ao salvar data de atualização: {e}")


def load_cards_sent():
    if not os.path.exists(CARDS_SENT_FILE):
        return {}
    try:
        with open(CARDS_SENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {k: set(v) for k, v in data.items()}
    except Exception as e:
        logger.error(f"Erro ao carregar cards enviados: {e}")
        return {}


def save_cards_sent(cards_sent: dict):
    try:
        serializable = {k: list(v) for k, v in cards_sent.items()}
        with open(CARDS_SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar cards enviados: {e}")

