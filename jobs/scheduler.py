import logging
from telegram.ext import JobQueue, CallbackContext
from datetime import time as dt_time 
from zoneinfo import ZoneInfo         
from utils.files import load_chat_ids
from config import GALACTUS_CHAT_ID
from utils.helpers import send_cosmic_roulette
from handlers.polls import send_single_card_poll

logger = logging.getLogger(__name__)
TZ = ZoneInfo("America/Sao_Paulo") 

def schedule_polls_for_chat(job_queue, chat_id: int):
    poll_base_name = f"hourly_poll_{chat_id}"

    for hour in range(7, 23):          
        job_name = f"{poll_base_name}_{hour:02d}"

        if job_queue.get_jobs_by_name(job_name):
            continue

        job_queue.run_daily(
            send_single_card_poll,
            time=dt_time(hour=hour, minute=15, tzinfo=TZ),
            name=job_name,
            data={"chat_id": chat_id},
        )

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
                time=dt_time(hour=17, minute=0, tzinfo=TZ),
                data={"chat_id": chat_id},
                name=roulette_name,
            )

        if str(chat_id) == str(GALACTUS_CHAT_ID):
            schedule_polls_for_chat(job_queue, chat_id)

