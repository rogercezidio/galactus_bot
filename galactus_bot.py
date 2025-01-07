import os
import re
import telegram 
import json
import time
import base64
import random
import logging
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from datetime import time as dt_time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, JobQueue, JobQueue

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TOKEN = os.getenv('BOT_TOKEN')
print(f"Bot Token: {TOKEN}")  

if TOKEN is None:
    print("Error: BOT_TOKEN environment variable is not set.")
    exit(1)

GALACTUS_CHAT_ID = os.getenv("GALACTUS_CHAT_ID")
if GALACTUS_CHAT_ID is None:
    logger.error("GALACTUS_CHAT_ID environment variable is not set.")
    exit(1)

chat_cooldowns = {}
last_updated_date = None
chat_ids = set()

COOLDOWN_TIME = 60
RANK_FILE_PATH = '/app/data/rankings.json'
DECK_LIST_URL = 'https://marvelsnapzone.com/tier-list/'
UPDATE_FILE_PATH = '/app/data/last_update.txt'  
CHAT_IDS_FILE_PATH = '/app/data/chat_ids.json'
USER_IDS_FILE_PATH = '/app/data/user_ids.json'
GALACTUS_GIF_URL = "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExc2Z4amt5dTVlYWEycmZ4bjJ1MzIwemViOTBlcGN1eXVkMXcxcXZzbiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7QL0aLRbHtAyc/giphy.gif"
GALACTUS_WELCOME_GIF_URL= "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExZTQwb2dzejFrejhyMjc4NWh1OThtMW1vOGxvMzVwd3NtOXo2YWZhMyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xT1XGCiATaxXxW7pp6/giphy-downsized-large.gif"

GROUP_RULES = """
Proibido:
1 - Ofensas a pessoas e/ou opiniões.
2 - Pornografias.
3 - Política, religião ou assuntos q não levem a lugar algum (direita vs. esquerda tb).
4 - Spoilers.
5 - Pirataria.
6 - Pirâmides financeiras ou afins.
"""

GALACTUS_PATTERN = re.compile(r'''
    \b                 
    (                  
        g\s*           
        [a@4áàâãäå*]\s*  
        l\s* 
        [a@4qáàâãäå*]\s*    
        [cç]?\s*      
        [t7]?\s*       
        [uúùûü*]?\s*   
        [s$z]?\s*      
        |
        g[a-z@4qáàâãäå]l[a-z@4qáàâãäå]*t[aoõã]*o 
        |           
        g[a4]l[a4]ctus 
        |            
        g[a4]l[a4]k[t7]us 
        |              
        ギャラクタス     
        |              
        갈락투스         
        |              
        Галактус      
        |              
        جالكتوس        
        |              
        银河吞噬者       
        |              
        गैलैक्टस          
        |             
        גלקטוס         
        |             
        galatus        
        |              
        galaquitus     
        |              
        galacta        
    )                  
    \b                 
''', re.VERBOSE | re.IGNORECASE)

def load_chat_ids():
    """Load chat IDs from the JSON file and return them as a list of dictionaries."""
    if not os.path.exists(CHAT_IDS_FILE_PATH):
        logger.warning(f"Chat ID file not found at {CHAT_IDS_FILE_PATH}")
        return []
    
    try:
        with open(CHAT_IDS_FILE_PATH, 'r') as file:
            data = json.load(file)
            chats = data.get("chats", [])
            logger.info(f"Loaded {len(chats)} chat(s) from JSON file.")
            return chats
    except Exception as e:
        logger.error(f"Failed to load chat IDs from JSON file: {e}")
        return []


def save_chat_ids(chat_ids):
    """Save chat IDs and names to the JSON file."""
    try:
        data = {"chats": chat_ids}

        with open(CHAT_IDS_FILE_PATH, 'w') as file:
            json.dump(data, file, indent=4)
        
        logger.info(f"Saved {len(chat_ids)} chat ID(s) to file.")
    except Exception as e:
        logger.error(f"Failed to save chat IDs: {e}")

def load_last_updated_date():
    global last_updated_date
    if os.path.exists(UPDATE_FILE_PATH):
        with open(UPDATE_FILE_PATH, 'r') as file:
            last_updated_date = file.read().strip()
            logger.info(f"Loaded last updated date from file: {last_updated_date}")
    else:
        logger.info("No previous update date found.")

def save_last_updated_date(date):
    global last_updated_date
    last_updated_date = date
    with open(UPDATE_FILE_PATH, 'w') as file:
        file.write(date)
        logger.info(f"Saved new updated date to file: {last_updated_date}")

def fetch_updated_date():
    try:
        response = requests.get(DECK_LIST_URL)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        figcaption_element = soup.find('figcaption')
        
        if figcaption_element and 'Updated:' in figcaption_element.get_text():
            updated_text = figcaption_element.get_text(strip=True)
            
            updated_date = updated_text.split("Updated:")[1].strip()
            
            return updated_date
        else:
            print("Could not find the updated date element.")
            return None
    except Exception as e:
        print(f"Error fetching the updated date: {e}")
        return None

async def check_for_update(context: CallbackContext):
    global last_updated_date
    current_date = fetch_updated_date()

    if current_date is not None:
        if last_updated_date is None:
            save_last_updated_date(current_date)
        elif current_date != last_updated_date:
            logger.info(f"Tier list updated! New date: {current_date}")
            save_last_updated_date(current_date)

            reply_markup = get_decks_keyboard()

            chats = load_chat_ids()
            if not chats:
                logger.warning("No chats to notify meta changes.")
                return
            
            for chat in chats:
                chat_id = chat.get("chat_id")
                if chat_id is not None:
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="O meta foi atualizado! Confira:",
                            reply_markup=reply_markup
                        )
                        logger.info(f"Message sent to chat {chat_id}")
                    except Exception as e:
                        logger.error(f"Failed to send message to chat {chat_id}: {e}")
        else:
            logger.info(f"No update detected. Last updated date is still: {last_updated_date}")
    else:
        logger.error("Failed to fetch updated date.")

def get_decks_keyboard():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0'
    }
    response = requests.get(DECK_LIST_URL, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        tables = soup.find_all('table')
        if tables:
            table = tables[0]
            keyboard = []
            for row in table.find_all('tr')[1:]:
                columns = row.find_all('td')
                if len(columns) == 2:
                    tier = columns[0].text.strip()
                    deck_name = columns[1].text.strip()
                    link_tag = columns[1].find('a')
                    deck_link = link_tag['href'] if link_tag else None
                    keyboard.append([
                        InlineKeyboardButton(f"{tier}: {deck_name}", url=deck_link)
                    ])
            return InlineKeyboardMarkup(keyboard)
        else:
            return None
    else:
        return None
    
async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    chat_name = update.effective_chat.title or update.effective_chat.first_name
    existing_chats = load_chat_ids()

    if not any(chat['chat_id'] == chat_id for chat in existing_chats):
        existing_chats.append({"name": chat_name, "chat_id": chat_id})
        logger.info(f"New chat ID added: {chat_id} ({chat_name})")

        save_chat_ids(existing_chats)

    await update.message.reply_text('Olá! Eu sou o Galactus Bot. Estou ouvindo...')

async def decks(update: Update, context: CallbackContext) -> None:
    global last_updated_date  

    reply_markup = get_decks_keyboard()

    if last_updated_date:
        message = f"Selecione um deck para visualizar:\n\nÚltima atualização: {last_updated_date}"
    else:
        message = "Selecione um deck para visualizar:\n\nÚltima atualização: Data desconhecida"

    if reply_markup:
        await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text('Failed to retrieve deck information.')

async def get_user_profile_photo(user_id, bot):
    photos = await bot.get_user_profile_photos(user_id)
    if photos.total_count > 0:
        file_id = photos.photos[0][-1].file_id
        file = await bot.get_file(file_id)
        file_path = os.path.join(Path(__file__).parent, f"{user_id}_photo.jpg")
        
        await file.download_to_drive(file_path)
        
        return file_path
    return None

def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logging.error(f"Erro ao codificar a imagem: {e}")
        return None

async def generate_galactus_roast(user_first_name, profile_photo_path):
    try:
        base64_image = encode_image(profile_photo_path)
        if not base64_image:
            raise ValueError("Erro ao codificar a imagem do perfil.")

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Descreva esta imagem em português."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {client.api_key}"},
            json=payload
        )
        response.raise_for_status()  
        image_description = response.json()['choices'][0]['message']['content']

        roast_prompt = f"Galactus está prestes a humilhar um humano chamado {user_first_name}. Aqui está a descrição da imagem de perfil desse usuário: {image_description}. Escreva um insulto humilhante, sarcástico e devastador baseado nessa descrição."

        roast_response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é Galactus, o devorador de mundos. Humilhe este humano de forma curta e grossa como só Galactus pode, mencionando seu nome e usando a imagem descrita."},
                {"role": "user", "content": roast_prompt}
            ],
            model="gpt-3.5-turbo",
        )

        roast_text = roast_response.choices[0].message.content

        return roast_text, None 

    except Exception as e:
        logging.error(f"Erro ao gerar o insulto de Galactus: {e}")
        return f"{user_first_name}, você nem é digno de uma humilhação do devorador de mundos.", None

async def roast_user(update: Update, context: CallbackContext) -> None:
    user_first_name = update.message.from_user.first_name  
    user_id = update.message.from_user.id

    profile_photo_path = await get_user_profile_photo(user_id, context.bot)
    
    roast_message, _ = await generate_galactus_roast(user_first_name, profile_photo_path)  

    await update.message.reply_text(f"{roast_message}")
        
    await context.bot.send_animation(chat_id=update.effective_chat.id, animation=GALACTUS_GIF_URL)

async def daily_curse_by_galactus(update: Update, context: CallbackContext) -> None:
    message = update.message
    if update.message and update.message.text:
        message_text = update.message.text.lower()

        if re.search(GALACTUS_PATTERN, message_text):
            chat_id = message.chat.id

            if str(chat_id) == str(GALACTUS_CHAT_ID):
                random_value = random.random()
                print(f"Random value: {random_value}")

                if random_value < 0.25:
                    await roast_user(update, context)

                else:
                    await update.message.reply_text("Banido!")
                    await context.bot.send_animation(chat_id=update.effective_chat.id, animation=GALACTUS_GIF_URL)
            else:
                logger.info(f"Received a message from chat_id {chat_id} which is not the specified GALACTUS_CHAT_ID.")
    else:
        logger.warning("Received an update without a message or text")

async def send_spotlight_link(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id 
    current_time = time.time()

    if chat_id in chat_cooldowns:
        last_execution_time = chat_cooldowns[chat_id]
        elapsed_time = current_time - last_execution_time

        if elapsed_time < COOLDOWN_TIME:
            remaining_time = COOLDOWN_TIME - elapsed_time
            return

    chat_cooldowns[chat_id] = current_time

    keyboard = [
        [InlineKeyboardButton("Baús de Destaque", url="https://marvelsnapzone.com/spotlight-caches/")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Clique no botão abaixo para ver os próximos baús de destaque:", reply_markup=reply_markup)

async def generate_galactus_welcome(user_first_name):
    try:
        prompt = f"Galactus está prestes a receber um novo humano no grupo de jogadores de Marvel Snap. O nome do humano é {user_first_name}. Dê boas-vindas a ele, mas de forma amigável e poderosa, como só Galactus poderia fazer. Não se esqueça de mencioná-lo pelo nome."
        
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é Galactus, o devorador de mundos. Dê boas-vindas aos novos humanos que entram no grupo de uma forma poderosa e amigável."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-3.5-turbo",
        )

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erro ao gerar a mensagem de boas-vindas do Galactus: {e}")
        return f"{user_first_name}, você foi notado por Galactus, o devorador de mundos. Bem-vindo, humano insignificante!"

async def welcome_user(update: Update, context: CallbackContext) -> None:
    for new_user in update.message.new_chat_members:
        user_first_name = new_user.first_name

        welcome_message = await generate_galactus_welcome(user_first_name)

        complete_message = f"{welcome_message}\n\nAqui estão as regras do grupo:\n{GROUP_RULES}"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=complete_message
        )
    
        await context.bot.send_animation(
            chat_id=update.effective_chat.id, 
            animation=GALACTUS_WELCOME_GIF_URL
        )

async def generate_galactus_farewell(user_first_name):
    try:
        prompt = f"Galactus está prestes a se despedir de um humano chamado {user_first_name}, que acabou de sair de um grupo. Escreva uma mensagem sarcástica e devastadora de despedida."

        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é Galactus, o devorador de mundos. Despeça-se dos humanos que deixam o grupo de uma forma poderosa e sarcástica."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-3.5-turbo",
        )

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erro ao gerar a mensagem de despedida do Galactus: {e}")
        return f"{user_first_name}, você acha que pode escapar da ira de Galactus? Insignificante!"

async def user_left_group(update: Update, context: CallbackContext) -> None:
    user_first_name = update.message.left_chat_member.first_name

    farewell_message = await generate_galactus_farewell(user_first_name)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=farewell_message
    )

    await context.bot.send_animation(
        chat_id=update.effective_chat.id,
        animation=GALACTUS_GIF_URL
    )

async def send_scheduled_link(context: CallbackContext, chat_id: int) -> None:
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

    keyboard = [
        [InlineKeyboardButton("Girar a roleta cósmica", url=link)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_animation(chat_id=chat_id, animation=gif_url)

    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode='Markdown')

def schedule_link_jobs_for_all_chats(job_queue: JobQueue):
    """Schedule the message for all chat IDs saved in the JSON file."""
    chats = load_chat_ids()
    if not chats:
        logger.info("No chat IDs found to schedule.")
        return
    
    for chat in chats:
        chat_name = chat.get("name", "Unknown Chat")
        chat_id = chat.get("chat_id")
        if chat_id is not None:
            schedule_link_jobs(job_queue, chat_name, chat_id)
        else:
            logger.warning(f"Missing chat_id for chat '{chat_name}'.")

def schedule_link_jobs(job_queue: JobQueue, chat_name: str, chat_id: int):
    """Schedules the link sending for a specific chat with a unique job name."""
    async def send_link_wrapper(context: CallbackContext) -> None:
        await send_scheduled_link(context, chat_id)

    job_name = f"send_link_wrapper_{chat_id}"
    logger.info(f"Scheduling job for chat '{chat_name}' with chat_id: {chat_id} and job_name: {job_name}")

    job_queue.run_daily(
        send_link_wrapper,  
        time=dt_time(hour=20, minute=00),
        days=(2, 5, 0),
        name=job_name
    )

async def galactus_reply(update: Update, context: CallbackContext):
    message = update.message

    if message is None:
        logger.error("Received an update with no message.")
        return

    chat_id = message.chat.id
    user_message = message.text

    if str(chat_id) == str(GALACTUS_CHAT_ID):
        is_reply_to_this_bot = (
            message.reply_to_message and
            message.reply_to_message.from_user and
            message.reply_to_message.from_user.is_bot and
            (message.reply_to_message.from_user.id == context.bot.id)
        )

        is_bot_mentioned = False
        if message.entities:
            for entity in message.entities:
                if entity.type == 'mention':
                    mentioned_username = message.text[entity.offset:entity.offset + entity.length]
                    if mentioned_username.lower() == f'@{context.bot.username.lower()}':
                        is_bot_mentioned = True
                        break
                elif entity.type == 'text_mention':
                    if entity.user and (entity.user.id == context.bot.id):
                        is_bot_mentioned = True
                        break

        if is_reply_to_this_bot or is_bot_mentioned:
            try:
                prompt = (
                    f"Imite Galactus em uma conversa. Responda à seguinte mensagem "
                    f"com a personalidade e o tom de Galactus:\nMensagem: {user_message}"
                )

                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Você é Galactus, o Devorador de Mundos."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150
                )

                galactus_response = response.choices[0].message.content
                await context.bot.send_message(chat_id=chat_id, text=galactus_response)

            except Exception as e:
                logger.error(f"Erro ao gerar resposta do Galactus: {e}")
                await message.reply_text("Até Galactus comete erros...")
        else:
            logger.info("Message not directed to the bot. Doing nothing.")
    else:
        logger.info(f"Received a message from chat_id {chat_id} which is not the specified GALACTUS_CHAT_ID.")

mention_filter = filters.Entity("mention") | filters.Entity("text_mention")

def main():
    print("Starting bot...")

    load_last_updated_date()

    load_chat_ids()

    application = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    schedule_link_jobs_for_all_chats(application.job_queue)

    galactus_filter = filters.TEXT & (~filters.COMMAND) & (filters.Regex(GALACTUS_PATTERN))

    application.add_handler(MessageHandler(galactus_filter, daily_curse_by_galactus))

    application.add_handler(MessageHandler(mention_filter, galactus_reply))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("decks", decks))
    application.add_handler(CommandHandler("spotlight", send_spotlight_link))

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))

    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, user_left_group))

    job_queue = application.job_queue
    job_queue.run_repeating(check_for_update, interval=1800, first=10)

    application.run_polling()
    print("Bot is polling...")

if __name__ == '__main__':
    main()
