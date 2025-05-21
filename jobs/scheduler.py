import logging
from telegram.ext import JobQueue, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import time as dt_time # Para especificar a hora do job diário
from utils.files import load_chat_ids

logger = logging.getLogger(__name__)

# --- Exemplo de função de callback para um job agendado ---
async def send_daily_reminder_link(context: CallbackContext):
    """
    Função de callback exemplo que envia uma mensagem com um link.
    O job_context pode ser usado para passar dados específicos, como o chat_id.
    """
    job_data = context.job.data
    chat_id = job_data.get("chat_id")
    
    if not chat_id:
        logger.error("Job 'send_daily_reminder_link' executado sem chat_id nos dados.")
        return

    # Exemplo de mensagem e link
    message_text = (
        "🔮 Lembrete do Oráculo Galactus! 🔮\n\n"
        "Não se esqueça de conferir as novidades e estratégias do dia no Marvel Snap Zone!"
    )
    link_url = "https://marvelsnapzone.com/" # Exemplo de link
    keyboard = [[InlineKeyboardButton("Visitar Marvel Snap Zone", url=link_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=reply_markup
        )
        logger.info(f"Lembrete diário com link enviado para o chat ID: {chat_id}")
    except Exception as e:
        logger.error(f"Falha ao enviar lembrete diário para o chat ID {chat_id}: {e}")

# --- Função principal de agendamento ---
def schedule_link_jobs_for_all_chats(job_queue: JobQueue):
    """
    Agenda jobs que enviam links ou mensagens periódicas para todos os chats cadastrados.
    """
    logger.info("Agendando 'link jobs' para todos os chats...")
    
    chat_ids_data = load_chat_ids() # Esta função já está em utils/files

    if not chat_ids_data:
        logger.warning("Nenhum chat ID encontrado para agendar 'link jobs'.")
        return

    for chat_info in chat_ids_data:
        chat_id = chat_info.get("chat_id")
        chat_name = chat_info.get("name", f"ID_{chat_id}") # Usa o nome do chat se disponível

        if chat_id:
            # Exemplo: Agendar o envio do 'send_daily_reminder_link' para cada chat
            # Este job rodará todos os dias às 10:00 (horário do servidor onde o bot roda)
            job_name = f"daily_reminder_link_{chat_id}"
            
            # Verifica se um job com o mesmo nome já existe para evitar duplicação
            # se esta função for chamada múltiplas vezes (embora não deva ser o caso aqui)
            current_jobs = job_queue.get_jobs_by_name(job_name)
            if not current_jobs:
                job_queue.run_daily(
                    send_daily_reminder_link,
                    time=dt_time(hour=10, minute=0, second=0), # Ex: 10:00 AM
                    data={"chat_id": chat_id}, # Passa o chat_id para o callback
                    name=job_name
                )
                logger.info(f"Job '{job_name}' agendado para o chat '{chat_name}' (ID: {chat_id}).")
            else:
                logger.info(f"Job '{job_name}' já existe para o chat '{chat_name}' (ID: {chat_id}). Não será reagendado.")
        else:
            logger.warning(f"Chat info sem chat_id encontrado ao agendar jobs: {chat_info}")
            
    logger.info(f"Agendamento de 'link jobs' concluído para {len(chat_ids_data)} chats (se houver).")

