import logging
from telegram.ext import JobQueue, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import time as dt_time  # Para especificar a hora do job diário
from utils.files import load_chat_ids
from utils.helpers import send_cosmic_roulette

logger = logging.getLogger(__name__)

# --- Função de callback para roleta cósmica ---
async def send_cosmic_roulette_job(context: CallbackContext):
    job_data = context.job.data
    chat_id = job_data.get("chat_id")
    if not chat_id:
        logger.error("Job 'send_cosmic_roulette_job' executado sem chat_id nos dados.")
        return
    try:
        await send_cosmic_roulette(context, chat_id)
        logger.info(f"Roleta cósmica enviada para o chat ID: {chat_id}")
    except Exception as e:
        logger.error(f"Falha ao enviar roleta cósmica para o chat ID {chat_id}: {e}")

# --- Função principal de agendamento ---
def schedule_link_jobs_for_all_chats(job_queue: JobQueue):
    """
    Agenda jobs que enviam links ou mensagens periódicas para todos os chats cadastrados.
    """
    logger.info("Agendando 'link jobs' para todos os chats...")

    chat_ids_data = load_chat_ids()  # Esta função já está em utils/files

    if not chat_ids_data:
        logger.warning("Nenhum chat ID encontrado para agendar 'link jobs'.")
        return

    for chat_info in chat_ids_data:
        chat_id = chat_info.get("chat_id")
        chat_name = chat_info.get(
            "name", f"ID_{chat_id}"
        )  # Usa o nome do chat se disponível

        if chat_id:
            # Agendamento da roleta cósmica
            roulette_job_name = f"cosmic_roulette_{chat_id}"
            roulette_jobs = job_queue.get_jobs_by_name(roulette_job_name)
            if not roulette_jobs:
                job_queue.run_daily(
                    send_cosmic_roulette_job,
                    time=dt_time(hour=20, minute=0, second=0),  
                    data={"chat_id": chat_id},
                    name=roulette_job_name,
                )
                logger.info(
                    f"Job '{roulette_job_name}' agendado para o chat '{chat_name}' (ID: {chat_id})."
                )
            else:
                logger.info(
                    f"Job '{roulette_job_name}' já existe para o chat '{chat_name}' (ID: {chat_id}). Não será reagendado."
                )
        else:
            logger.warning(
                f"Chat info sem chat_id encontrado ao agendar jobs: {chat_info}"
            )

    logger.info(
        f"Agendamento de 'link jobs' concluído para {len(chat_ids_data)} chats (se houver)."
    )
