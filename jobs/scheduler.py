import logging
from telegram.ext import JobQueue, CallbackContext
from datetime import time as dt_time 
from utils.files import load_chat_ids
from utils.helpers import send_cosmic_roulette
from handlers.polls import enviar_enquete_carta_unica

logger = logging.getLogger(__name__)

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

def schedule_link_jobs_for_all_chats(job_queue: JobQueue):
    logger.info("Agendando jobs…")
    for info in load_chat_ids():
        chat_id = info.get("chat_id")
        if not chat_id:
            logger.warning("Registro sem chat_id: %s", info)
            continue

        roulette_name = f"cosmic_roulette_{chat_id}"
        if not job_queue.get_jobs_by_name(roulette_name):
            job_queue.run_daily(
                send_cosmic_roulette_job,
                time=dt_time(hour=20, minute=0),
                data={"chat_id": chat_id},
                name=roulette_name,
            )

        poll_name = f"hourly_poll_{chat_id}"
        if not job_queue.get_jobs_by_name(poll_name):
            job_queue.run_repeating(
                enviar_enquete_carta_unica,
                interval=60*60,     
                first=30,       
                name=poll_name,
                data={"chat_id": chat_id},
            )