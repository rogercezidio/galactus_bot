import os
import re
import telegram  # <-- Make sure to import the telegram module
import json
import time
import base64
import random
import logging
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from functools import partial
from openai import AsyncOpenAI
from datetime import time as dt_time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Enable logging to debug if needed
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set your OpenAI API key
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get the bot token from an environment variable
TOKEN = os.getenv('BOT_TOKEN')
print(f"Bot Token: {TOKEN}")  # Debugging: Check if the token is being retrieved

if TOKEN is None:
    print("Error: BOT_TOKEN environment variable is not set.")
    exit(1)

# Dictionary to store the last execution time for each chat
chat_cooldowns = {}
# Global dictionary to track user ids based on username
last_updated_date = None
# Set to store chat IDs
chat_ids = set()

# Cooldown time in seconds (e.g., 10 seconds)
COOLDOWN_TIME = 60
RANK_FILE_PATH = '/app/data/rankings.json'
DECK_LIST_URL = 'https://marvelsnapzone.com/tier-list/'
UPDATE_FILE_PATH = '/app/data/last_update.txt'  # Make sure this matches the volume mount path
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
    \b                 # Word boundary
    (                  # Begin group
        g\s*           # 'g' with optional spaces
        [a@4áàâãäå*]\s*  # 'a' with accented characters and creative variations
        l\s*           # 'l' with optional spaces
        [a@4qáàâãäå*]\s*    # 'a' with accented characters, '@', '4', 'q', '#' with optional spaces
        [cç]?\s*       # Optional 'c' or 'ç', with optional spaces (for 'galatus')
        [t7]\s*        # 't' or '7' with optional spaces
        [uúùûü*]\s*    # 'u' with accented characters or '*' with optional spaces
        [s$z]\s*       # 's', 'z', or '$' with optional spaces
        |              # OR
        g[a-z@4qáàâãäå]l[a-z@4qáàâãäå]*t[aoõã]*o  # Handle variations like 'galatão', 'galaquitus', 'galatã'
        |              # OR
        g[a4]l[a4]ctus # Handle variations like 'g4l4ctus'
        |              # OR
        g[a4]l[a4]k[t7]us # Handle 'galaktus' variations with 'k'
        |              # OR
        ギャラクタス     # Japanese characters for 'Galactus'
        |              # OR
        갈락투스         # Korean characters for 'Galactus'
        |              # OR
        Галактус       # Cyrillic (Russian) for 'Galactus'
        |              # OR
        جالكتوس        # Arabic for 'Galactus'
        |              # OR
        银河吞噬者       # Chinese for 'Galactus' (literally 'Galactic Devourer')
        |              # OR
        गैलैक्टस          # Hindi for 'Galactus'
        |              # OR
        גלקטוס         # Hebrew for 'Galactus'
        |              # OR
        galatus        # Specifically capture 'galatus'
        |              # OR
        galaquitus     # Specifically capture 'galaquitus'
    )                  # End group
    \b                 # Word boundary
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
        # Prepare the data to be saved
        data = {"chats": chat_ids}

        # Write the data to the JSON file
        with open(CHAT_IDS_FILE_PATH, 'w') as file:
            json.dump(data, file, indent=4)
        
        logger.info(f"Saved {len(chat_ids)} chat ID(s) to file.")
    except Exception as e:
        logger.error(f"Failed to save chat IDs: {e}")

# Function to load the last updated date from a file
def load_last_updated_date():
    global last_updated_date
    if os.path.exists(UPDATE_FILE_PATH):
        with open(UPDATE_FILE_PATH, 'r') as file:
            last_updated_date = file.read().strip()
            logger.info(f"Loaded last updated date from file: {last_updated_date}")
    else:
        logger.info("No previous update date found.")

# Function to save the updated date to a file
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
        
        # Search for the <figcaption> element
        figcaption_element = soup.find('figcaption')
        
        if figcaption_element and 'Updated:' in figcaption_element.get_text():
            # Extract the date, which should be within the text following "Updated:"
            updated_text = figcaption_element.get_text(strip=True)
            
            # The date is expected to be after "Updated:", so split and strip it
            updated_date = updated_text.split("Updated:")[1].strip()
            
            return updated_date
        else:
            print("Could not find the updated date element.")
            return None
    except Exception as e:
        print(f"Error fetching the updated date: {e}")
        return None

# Function to check if the tier list is updated and notify users
async def check_for_update(context: CallbackContext):
    global last_updated_date
    current_date = fetch_updated_date()

    if current_date is not None:
        if last_updated_date is None:
            save_last_updated_date(current_date)
        elif current_date != last_updated_date:
            logger.info(f"Tier list updated! New date: {current_date}")
            save_last_updated_date(current_date)

            # Create an inline button that links to the updated tier list
            reply_markup = get_decks_keyboard()

            # Notify all users whose chat IDs are persisted
            if chat_ids:
                logger.info(f"Notifying {len(chat_ids)} chat(s)")

                for chat_id in chat_ids:
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
                logger.warning("No chats to notify.")
        else:
            logger.info(f"No update detected. Last updated date is still: {last_updated_date}")
    else:
        logger.error("Failed to fetch updated date.")

# Function to fetch deck list and create inline keyboard
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
                    # Create an inline button for each deck
                    keyboard.append([
                        InlineKeyboardButton(f"{tier}: {deck_name}", url=deck_link)
                    ])
            return InlineKeyboardMarkup(keyboard)
        else:
            return None
    else:
        return None
    
# Updated start command handler to also schedule the link jobs
async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    chat_name = update.effective_chat.title or update.effective_chat.first_name
    # Load existing chat IDs
    existing_chats = load_chat_ids()

    # Check if the chat ID already exists
    if not any(chat['chat_id'] == chat_id for chat in existing_chats):
        # Add the new chat ID and name
        existing_chats.append({"name": chat_name, "chat_id": chat_id})
        logger.info(f"New chat ID added: {chat_id} ({chat_name})")

        # Persist chat IDs to file
        save_chat_ids(existing_chats)

    await update.message.reply_text('Olá! Eu sou o Galactus Bot. Estou ouvindo...')

async def decks(update: Update, context: CallbackContext) -> None:
    global last_updated_date  # Ensure we're accessing the global last updated date

    reply_markup = get_decks_keyboard()

    if last_updated_date:
        # If we have the last updated date, include it in the message
        message = f"Selecione um deck para visualizar:\n\nÚltima atualização: {last_updated_date}"
    else:
        # If no date is available, indicate that the date is unknown
        message = "Selecione um deck para visualizar:\n\nÚltima atualização: Data desconhecida"

    if reply_markup:
        await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text('Failed to retrieve deck information.')

async def get_user_profile_photo(user_id, bot):
    photos = await bot.get_user_profile_photos(user_id)
    if photos.total_count > 0:
        # Get the largest size photo
        file_id = photos.photos[0][-1].file_id
        file = await bot.get_file(file_id)
        file_path = os.path.join(Path(__file__).parent, f"{user_id}_photo.jpg")
        
        # Download the file using the correct async method
        await file.download_to_drive(file_path)
        
        return file_path
    return None

# Function to encode the image
def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logging.error(f"Erro ao codificar a imagem: {e}")
        return None

async def generate_galactus_roast(user_first_name, profile_photo_path):
    try:
        # Encode the user's profile picture to base64
        base64_image = encode_image(profile_photo_path)
        if not base64_image:
            raise ValueError("Erro ao codificar a imagem do perfil.")

        # Step 1: Describe the image
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
        response.raise_for_status()  # Check for HTTP errors
        image_description = response.json()['choices'][0]['message']['content']

        # Step 2: Use the description to generate the roast
        roast_prompt = f"Galactus está prestes a humilhar um humano chamado {user_first_name}. Aqui está a descrição da imagem de perfil desse usuário: {image_description}. Escreva um insulto humilhante, sarcástico e devastador baseado nessa descrição."

        # Generate the roast text using the chat API
        roast_response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é Galactus, o devorador de mundos. Humilhe este humano de forma curta e grossa como só Galactus pode, mencionando seu nome e usando a imagem descrita."},
                {"role": "user", "content": roast_prompt}
            ],
            model="gpt-3.5-turbo",
        )

        roast_text = roast_response.choices[0].message.content

        return roast_text, None  # Ensure exactly two values are returned

    except Exception as e:
        logging.error(f"Erro ao gerar o insulto de Galactus: {e}")
        return f"{user_first_name}, você nem é digno de uma humilhação do devorador de mundos.", None

# Function to roast the user
async def roast_user(update: Update, context: CallbackContext) -> None:
    user_first_name = update.message.from_user.first_name  # Get the user's first name
    user_id = update.message.from_user.id

    # Get the user's profile photo (if available)
    profile_photo_path = await get_user_profile_photo(user_id, context.bot)
    
    # Generate the roast with the user's name and photo
    roast_message, _ = await generate_galactus_roast(user_first_name, profile_photo_path)  # Generate the roast

    # Send the roast message
    await update.message.reply_text(f"{roast_message}")
        
    # Optionally, send a Galactus GIF for effect
    await context.bot.send_animation(chat_id=update.effective_chat.id, animation=GALACTUS_GIF_URL)

async def daily_curse_by_galactus(update: Update, context: CallbackContext) -> None:
    # Ensure that update.message exists and has text before proceeding
    if update.message and update.message.text:
        message_text = update.message.text.lower()

        # Check if the message mentions "Galactus"
        if re.search(GALACTUS_PATTERN, message_text):
            random_value = random.random()
            print(f"Random value: {random_value}")  # Debugging

            if random_value < 0.25:
                # 25% chance to roast the user
                await roast_user(update, context)
                await update.message.delete()

            else:
                # Default response: "Banido!" and send the Galactus GIF
                await update.message.reply_text("Banido!")
                await context.bot.send_animation(chat_id=update.effective_chat.id, animation=GALACTUS_GIF_URL)
    else:
        logger.warning("Received an update without a message or text")

# Function to handle the /spotlight command with a chat-based cooldown
async def send_spotlight_link(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id  # Get the chat's unique ID
    current_time = time.time()  # Get the current time in seconds

    # Check if the chat is on cooldown
    if chat_id in chat_cooldowns:
        last_execution_time = chat_cooldowns[chat_id]
        elapsed_time = current_time - last_execution_time

        if elapsed_time < COOLDOWN_TIME:
            # Cooldown still active, inform the user
            remaining_time = COOLDOWN_TIME - elapsed_time
            #await update.message.reply_text(f"The command is on cooldown in this chat. Please wait {int(remaining_time)}>
            return

    # Update the chat's last execution time
    chat_cooldowns[chat_id] = current_time

    # Create an inline keyboard with a button linking to the spotlight caches page
    keyboard = [
        [InlineKeyboardButton("Baús de Destaque", url="https://marvelsnapzone.com/spotlight-caches/")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with the inline keyboard button
    await update.message.reply_text("Clique no botão abaixo para ver os próximos baús de destaque:", reply_markup=reply_markup)

# Function to generate the welcome message using OpenAI
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

# Function to send welcome message when new members join (either by themselves or added by an admin)
async def welcome_user(update: Update, context: CallbackContext) -> None:
    # Iterate over all new chat members (handles cases where multiple members join)
    for new_user in update.message.new_chat_members:
        user_first_name = new_user.first_name

        # Generate the welcome message from Galactus
        welcome_message = await generate_galactus_welcome(user_first_name)

        # Complete welcome message with group rules
        complete_message = f"{welcome_message}\n\nAqui estão as regras do grupo:\n{GROUP_RULES}"

        # Send the welcome message to the chat
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=complete_message
        )
    
        # Optionally, send a Galactus GIF for added effect
        await context.bot.send_animation(
            chat_id=update.effective_chat.id, 
            animation=GALACTUS_WELCOME_GIF_URL
        )

# Function to generate the farewell message using OpenAI
async def generate_galactus_farewell(user_first_name):
    try:
        # Create the prompt for Galactus-style farewell message
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

# Function to handle when a user leaves the group
async def user_left_group(update: Update, context: CallbackContext) -> None:
    # Get the name of the user who left
    user_first_name = update.message.left_chat_member.first_name

    # Generate the farewell message using OpenAI
    farewell_message = await generate_galactus_farewell(user_first_name)

    # Send the farewell message to the group
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=farewell_message
    )

    # Optionally, send a Galactus GIF for effect
    await context.bot.send_animation(
        chat_id=update.effective_chat.id,
        animation=GALACTUS_GIF_URL
    )

# Updated main function to start the bot with only one CallbackQueryHandler
def main():
    print("Starting bot...")

    # Load the last known updated date from file
    load_last_updated_date()

    # Load chat IDs from file
    load_chat_ids()

    # Create the application
    application = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    schedule_link_jobs_for_all_chats(application.job_queue)

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("decks", decks))
    application.add_handler(CommandHandler("spotlight", send_spotlight_link))

    # Handler for welcoming new users
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))

    # Add a handler for users leaving the group
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, user_left_group))

    # Message handler for 'Galactus' keyword
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, daily_curse_by_galactus))

    # Run the periodic task every 30 minutes to check for tier list updates
    job_queue = application.job_queue
    job_queue.run_repeating(check_for_update, interval=1800, first=10)

    # Start the bot
    application.run_polling()
    print("Bot is polling...")

if __name__ == '__main__':
    main()