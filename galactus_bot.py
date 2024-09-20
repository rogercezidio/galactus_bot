import os
import re
import telegram  # <-- Make sure to import the telegram module
import json
import time
import logging
import random
import requests
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

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
user_ids = {}
user_data = {}
last_updated_date = None
# Set to store chat IDs
chat_ids = set()
game_state = {}

# Cooldown time in seconds (e.g., 10 seconds)
COOLDOWN_TIME = 60
RANK_FILE_PATH = '/app/data/rankings.json'
DECK_LIST_URL = 'https://marvelsnapzone.com/tier-list/'
UPDATE_FILE_PATH = '/app/data/last_update.txt'  # Make sure this matches the volume mount path
CHAT_IDS_FILE_PATH = '/app/data/chat_ids.txt'  # File to store chat IDs
USER_IDS_FILE_PATH = '/app/data/user_ids.json'
GAME_STATE_FILE_PATH = '/app/data/game_state.json'
GALACTUS_GIF_URL = "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExc2Z4amt5dTVlYWEycmZ4bjJ1MzIwemViOTBlcGN1eXVkMXcxcXZzbiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7QL0aLRbHtAyc/giphy.gif"
GALACTUS_WELCOME_GIF_URL= "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExZTQwb2dzejFrejhyMjc4NWh1OThtMW1vOGxvMzVwd3NtOXo2YWZhMyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xT1XGCiATaxXxW7pp6/giphy-downsized-large.gif"
ROULETTE_URL = "https://pay-va.nvsgames.com/topup/262304/eg-en?tab=purchase"

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

# Function to load chat IDs from a file
def load_chat_ids():
    global chat_ids
    if os.path.exists(CHAT_IDS_FILE_PATH):
        with open(CHAT_IDS_FILE_PATH, 'r') as file:
            ids = file.readlines()
            chat_ids = {int(chat_id.strip()) for chat_id in ids}
            logger.info(f"Loaded {len(chat_ids)} chat ID(s) from file.")
    else:
        logger.info("No previous chat IDs found. Chat ID file does not exist.")

# Function to save chat IDs to a file
def save_chat_ids():
    try:
        with open(CHAT_IDS_FILE_PATH, 'w') as file:
            for chat_id in chat_ids:
                file.write(f"{chat_id}\n")
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

def save_game_state(game_state):
    try:
        with open(GAME_STATE_FILE_PATH, 'w') as file:
            json.dump(game_state, file)
        logger.info("Game state saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save game state: {e}")

def load_game_state():
    try:
        if os.path.exists(GAME_STATE_FILE_PATH):
            with open(GAME_STATE_FILE_PATH, 'r') as file:
                state = json.load(file)
                logger.info(f"Game state loaded: {state}")
                return state
        else:
            logger.info("No previous game state found.")
            return {}
    except Exception as e:
        logger.error(f"Failed to load game state: {e}")
        return {}

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

# Start command handler
async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    # Add the chat ID to the set and save it to the file
    if chat_id not in chat_ids:
        chat_ids.add(chat_id)
        logger.info(f"New chat ID added: {chat_id}")
        save_chat_ids()  # Persist chat IDs to file

    user = update.message.from_user
    user_id = user.id
    username = user.username

    # Save the user ID if it is not already saved
    if username not in user_ids:
        user_ids[username] = user_id
        logger.info(f"New user registered: {username} with ID: {user_id}")
        save_user_ids()

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

# Function to generate a personalized roast using OpenAI
async def generate_galactus_roast(user_first_name):
    try:
        # Prompt for roasting the user by their name
        prompt = f"Galactus está prestes a humilhar um humano chamado {user_first_name}. Escreva um insulto sarcástico e devastador."
        
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é Galactus, o devorador de mundos. Humilhe este humano como só Galactus pode, mencionando seu nome."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-3.5-turbo",
        )

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Erro ao gerar o insulto de Galactus: {e}")
        return f"{user_first_name}, você nem é digno de uma humilhação do devorador de mundos."

# Function to roast the user
async def roast_user(update: Update, context: CallbackContext) -> None:
    user_first_name = update.message.from_user.first_name  # Get the user's first name
    roast_message = await generate_galactus_roast(user_first_name)  # Generate the roast

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

# Function to load user IDs from a file
def load_user_ids():
    global user_ids
    if os.path.exists(USER_IDS_FILE_PATH):
        try:
            with open(USER_IDS_FILE_PATH, 'r') as file:
                file_content = file.read().strip()
                if file_content:  # Only load if file is not empty
                    user_ids = json.loads(file_content)
                    logger.info(f"Loaded {len(user_ids)} user ID(s) from file.")
                else:
                    logger.warning("User ID file is empty. Initializing with an empty dictionary.")
                    user_ids = {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from file {USER_IDS_FILE_PATH}: {e}")
            user_ids = {}
    else:
        logger.info("No previous user IDs found. User ID file does not exist.")
        user_ids = {}

# Function to save user IDs to a file
def save_user_ids():
    try:
        if user_ids:  # Check if the dictionary has any data
            with open(USER_IDS_FILE_PATH, 'w') as file:
                json.dump(user_ids, file, indent=4)
            logger.info(f"Saved {len(user_ids)} user ID(s) to file: {user_ids}")
        else:
            logger.warning("No user IDs to save.")
    except Exception as e:
        logger.error(f"Failed to save user IDs: {e}")

# Load user IDs from a file (should be called in the bot startup)
def load_user_ids():
    global user_ids
    try:
        with open('/app/data/user_ids.json', 'r') as file:
            user_ids = json.load(file)
            logger.info(f"Loaded {len(user_ids)} user IDs from file.")
    except FileNotFoundError:
        logger.info("User ID file not found, starting fresh.")
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from user ID file, starting fresh.")
        user_ids = {}

# Save user IDs to a file
def save_user_ids():
    try:
        with open('/app/data/user_ids.json', 'w') as file:
            json.dump(user_ids, file)
            logger.info(f"Saved {len(user_ids)} user IDs to file.")
    except Exception as e:
        logger.error(f"Failed to save user IDs: {e}")

# Function to start a new Top Trumps game
async def start_top_trumps_game(update: Update, context: CallbackContext) -> None:
    global game_state
    
    user1_username = context.args[0].lstrip('@')
    user2_username = context.args[1].lstrip('@')
    
    # Verifique se ambos os usernames são iguais e corrija se necessário
    if user1_username == user2_username:
        user2_username = user1_username  # Ambos os usernames são iguais

    user1_id = user_ids.get(user1_username)
    user2_id = user_ids.get(user2_username)

    if user1_id is None or user2_id is None:
        await update.message.reply_text(f"Não foi possível encontrar o usuário @{user1_username}. Verifique o nome de usuário e tente novamente.")
        return

    # Captura o ID do chat do grupo diretamente do update
    group_chat_id = update.effective_chat.id
    logger.info(f"Starting Top Trumps game in group chat ID: {group_chat_id}")

    # Inicializa o estado do jogo com todas as chaves necessárias
    game_state = {
        "group_chat_id": group_chat_id,
        "user1": {"id": user1_id, "username": user1_username, "card": None, "score": 0},
        "user2": {"id": user2_id, "username": user2_username, "card": None, "score": 0},
        "round": 1,
        "multiplier": 1,  # Start with a 1x multiplier
        "user1_snap": False,
        "user2_snap": False
    }

    logger.info(f"Initial game state: {game_state}")

    # Mensagem de início de partida para o grupo
    start_message = (
        f"🎮 *A partida de Top Trumps começou!*\n\n"
        f"*{user1_username}* vs *{user2_username}*\n\n"
        f"Cada jogador deve escolher um atributo para competir. Que o melhor vença! 💪"
    )
    await context.bot.send_message(
        chat_id=group_chat_id,
        text=start_message,
        parse_mode='Markdown'
    )

    # Salva o estado inicial do jogo
    save_game_state(game_state)

    # Inicia o jogo
    await initiate_top_trumps_game(user1_id, user2_id, user1_username, user2_username, update, context)

# Function to initiate a round of Top Trumps
async def initiate_top_trumps_game(user1_id, user2_id, user1_username, user2_username, update, context):
    game_state = load_game_state()
    group_chat_id = game_state.get("group_chat_id")  # Usa o ID do grupo armazenado no game_state

    # Verifique se o game_state tem as chaves necessárias
    if "user1" not in game_state or "user2" not in game_state:
        logger.error("game_state is missing keys for user1 or user2")
        return

    # Sorteia cartas e armazena no estado do jogo
    user1_card = draw_card()
    user2_card = draw_card()
    
    # Atualiza o estado do jogo com as cartas sorteadas
    game_state["user1"]["card"] = user1_card
    game_state["user2"]["card"] = user2_card
    
    # Reset round states but keep the multiplier if it's already set
    if game_state["round"] == 1:
        game_state["multiplier"] = 1  # Reset multiplier only at the start of the game
    game_state["user1_snap"] = False
    game_state["user2_snap"] = False
    
    # Salva o estado do jogo com as cartas atualizadas
    save_game_state(game_state)

    # Formatação melhorada da mensagem
    message_text = (
        f"🎮 *Rodada {game_state['round']}*\n\n"
        f"✨ *{user1_username}*, você recebeu: *{user1_card['name']}*!\n\n"
        f"💪 **Força**: *{user1_card['força']}*\n"
        f"🧠 **Inteligência**: *{user1_card['inteligência']}*\n"
        f"🛡️ **Defesa**: *{user1_card['defesa']}*\n"
        f"⚡ **Velocidade**: *{user1_card['velocidade']}*\n\n"
        f"Escolha uma categoria para jogar contra *{user2_username}*:\n\n"
        f"🪙 *Pontos atuais*: {game_state['user1']['score']} vs {game_state['user2']['score']}\n"
    )

    # Cria botões para o user1 selecionar um atributo, com emojis para destacar, e adicionar a opção de Snap
    keyboard = [
        [InlineKeyboardButton("💪 Força", callback_data=f"força|{user1_id}|{user2_id}|{group_chat_id}")],
        [InlineKeyboardButton("🧠 Inteligência", callback_data=f"inteligência|{user1_id}|{user2_id}|{group_chat_id}")],
        [InlineKeyboardButton("🛡️ Defesa", callback_data=f"defesa|{user1_id}|{user2_id}|{group_chat_id}")],
        [InlineKeyboardButton("⚡ Velocidade", callback_data=f"velocidade|{user1_id}|{user2_id}|{group_chat_id}")],
        [InlineKeyboardButton("🔥 Snap", callback_data=f"snap|{user1_id}|{user2_id}|{group_chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Envia os detalhes da carta e os botões inline para o user1 no chat privado
    await context.bot.send_message(
        chat_id=user1_id, 
        text=message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Function to handle attribute choice
async def handle_attribute_choice(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    # Carrega o estado do jogo
    game_state = load_game_state()

    # Verifique se o game_state tem as chaves necessárias
    if "user1" not in game_state or "user2" not in game_state:
        logger.error("game_state is missing keys for user1 or user2")
        return

    # Extrai o ID do chat do grupo e outras informações do jogo
    group_chat_id = game_state.get("group_chat_id")
    round_number = game_state.get("round", 1)

    # Divide os dados do callback para extrair o atributo selecionado e IDs dos jogadores
    data = query.data.split("|")
    action = data[0]

    if action == "snap":
        user_id = int(data[1])
        if game_state["user1"]["id"] == user_id and not game_state.get("user1_has_snapped", False):
            game_state["user1_has_snapped"] = True
            game_state["multiplier"] *= 2
            await context.bot.send_message(chat_id=group_chat_id, text=f"{game_state['user1']['username']} usou Snap! Os pontos agora valem {game_state['multiplier']}x.")
        elif game_state["user2"]["id"] == user_id and not game_state.get("user2_has_snapped", False):
            game_state["user2_has_snapped"] = True
            game_state["multiplier"] *= 2
            await context.bot.send_message(chat_id=group_chat_id, text=f"{game_state['user2']['username']} usou Snap! Os pontos agora valem {game_state['multiplier']}x.")
        else:
            await query.message.reply_text("Você já usou Snap ou não é sua vez.")
        save_game_state(game_state)
        return  # End processing after a snap action

    # Handle normal attribute selection here
    attribute = action
    user1_id = int(data[1])
    user2_id = int(data[2])

    # Recupera as cartas dos jogadores
    user1_card = game_state["user1"]["card"]
    user2_card = game_state["user2"]["card"]

    # Determina o valor do atributo para ambos os jogadores
    user1_value = user1_card[attribute]
    user2_value = user2_card[attribute]

    # Determina o vencedor da rodada e atualiza a pontuação
    if user1_value > user2_value:
        result_message = (
            f"🏆 *{game_state['user1']['username']} venceu a rodada!*\n\n"
            f"🔍 *Atributo Escolhido:* {attribute.capitalize()}\n\n"
            f"🃏 *Carta de {game_state['user1']['username']}:* {user1_card['name']} | *{attribute.capitalize()}:* {user1_value}\n"
            f"🃏 *Carta de {game_state['user2']['username']}:* {user2_card['name']} | *{attribute.capitalize()}:* {user2_value}\n"
        )
        game_state["user1"]["score"] += game_state["multiplier"]  # Incrementa a pontuação do user1
    elif user1_value < user2_value:
        result_message = (
            f"🏆 *{game_state['user2']['username']} venceu a rodada!*\n\n"
            f"🔍 *Atributo Escolhido:* {attribute.capitalize()}\n\n"
            f"🃏 *Carta de {game_state['user2']['username']}:* {user2_card['name']} | *{attribute.capitalize()}:* {user2_value}\n"
            f"🃏 *Carta de {game_state['user1']['username']}:* {user1_card['name']} | *{attribute.capitalize()}:* {user1_value}\n"
        )
        game_state["user2"]["score"] += game_state["multiplier"]  # Incrementa a pontuação do user2
    else:
        result_message = (
            f"🤝 *Empate na rodada!*\n\n"
            f"🔍 *Atributo Escolhido:* {attribute.capitalize()}\n\n"
            f"🃏 *Carta de {game_state['user1']['username']}:* {user1_card['name']} | *{attribute.capitalize()}:* {user1_value}\n"
            f"🃏 *Carta de {game_state['user2']['username']}:* {user2_card['name']} | *{attribute.capitalize()}:* {user2_value}\n"
        )

    # Envia o resultado da rodada para o grupo
    await context.bot.send_message(
        chat_id=group_chat_id,
        text=result_message,
        parse_mode='Markdown'
    )

    # Verifica se o número máximo de rodadas foi atingido
    if round_number >= 5:
        user1_score = game_state["user1"]["score"]
        user2_score = game_state["user2"]["score"]

        if user1_score > user2_score:
            await end_game(update, context, winner_id=game_state['user1']['id'], winner_username=game_state['user1']['username'])
        elif user2_score > user1_score:
            await end_game(update, context, winner_id=game_state['user2']['id'], winner_username=game_state['user2']['username'])
        else:
            await context.bot.send_message(
                chat_id=group_chat_id,
                text=f"🤝 *O jogo terminou em empate, ambos os jogadores têm {user1_score} pontos!*",
                parse_mode='Markdown'
            )
            game_state = {}
            save_game_state(game_state)
    else:
        # Incrementa o número da rodada
        game_state["round"] += 1
        save_game_state(game_state)

        # Inicia a próxima rodada
        await initiate_top_trumps_game(
            game_state['user1']['id'], 
            game_state['user2']['id'], 
            game_state['user1']['username'], 
            game_state['user2']['username'], 
            update, 
            context
        )

def draw_card():
    # Example card data structure
    cards = [
        {"name": "Capitão América", "força": 70, "inteligência": 70, "defesa": 90, "velocidade": 65},
        {"name": "Homem de Ferro", "força": 80, "inteligência": 90, "defesa": 80, "velocidade": 75},
        {"name": "Thor", "força": 95, "inteligência": 60, "defesa": 85, "velocidade": 70},
        {"name": "Viúva Negra", "força": 60, "inteligência": 85, "defesa": 50, "velocidade": 80},
        {"name": "Hulk", "força": 100, "inteligência": 40, "defesa": 100, "velocidade": 50},
        # Add more cards as needed
    ]
    
    # Randomly select and return a card
    return random.choice(cards)

# Load or initialize the rank data
def load_rankings():
    if os.path.exists(RANK_FILE_PATH):
        with open(RANK_FILE_PATH, 'r') as file:
            return json.load(file)
    return {}

def save_rankings(rankings):
    with open(RANK_FILE_PATH, 'w') as file:
        json.dump(rankings, file, indent=4)  # Add indent for better readability in the file

def update_rankings(winner_id, loser_id, winner_points):
    # Load the current rankings
    rankings = load_rankings()
    
    # Ensure the winner is initialized in the rankings
    if winner_id not in rankings:
        rankings[winner_id] = 0
    
    # Accumulate the points
    rankings[winner_id] += winner_points
    
    # Debug: Print out the rankings before saving
    print(f"Updated Rankings: {rankings}")

    # Save the updated rankings
    save_rankings(rankings)

# Command to display the current rankings
async def rank(update: Update, context: CallbackContext) -> None:
    rankings = load_rankings()
    
    if not rankings:
        await update.message.reply_text("Ainda não há classificações disponíveis.")
        return

    # Sort the rankings by score in descending order
    sorted_rankings = sorted(rankings.items(), key=lambda item: item[1], reverse=True)
    
    # Generate the rank message
    rank_message = "🏆 *Classificação Atual*\n\n"
    for i, (user_id, score) in enumerate(sorted_rankings, start=1):
        user = await context.bot.get_chat(user_id)
        rank_message += f"{i}. {user.first_name} - {score} ponto(s)\n"
    
    await update.message.reply_text(rank_message, parse_mode='Markdown')

# Command to reset the rankings (admin only)
async def reset_rank(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id in context.bot_data.get('admins', []):
        save_rankings({})
        await update.message.reply_text("Classificações foram redefinidas.")
    else:
        await update.message.reply_text("Você não tem permissão para redefinir as classificações.")

# Command to Snap
async def snap(update: Update, context: CallbackContext) -> None:
    game_state = load_game_state()
    user_id = update.message.from_user.id
    
    if game_state["user1"]["id"] == user_id and not game_state["user1_snap"]:
        game_state["user1_snap"] = True
        game_state["multiplier"] *= 2
        await update.message.reply_text(f"{game_state['user1']['username']} usou Snap! Os pontos agora valem {game_state['multiplier']}x.")
    elif game_state["user2"]["id"] == user_id and not game_state["user2_snap"]:
        game_state["user2_snap"] = True
        game_state["multiplier"] *= 2
        await update.message.reply_text(f"{game_state['user2']['username']} usou Snap! Os pontos agora valem {game_state['multiplier']}x.")
    else:
        await update.message.reply_text("Você já usou Snap ou não é sua vez.")
    
    save_game_state(game_state)

# Command to Run
async def run(update: Update, context: CallbackContext) -> None:
    game_state = load_game_state()
    user_id = update.message.from_user.id
    
    if game_state["user1"]["id"] == user_id:
        await end_game(update, context, winner_id=game_state["user2"]["id"], winner_username=game_state['user2']['username'], reason="O adversário fugiu")
    elif game_state["user2"]["id"] == user_id:
        await end_game(update, context, winner_id=game_state["user1"]["id"], winner_username=game_state['user1']['username'], reason="O adversário fugiu")
    else:
        await update.message.reply_text("Você não está jogando.")

# Function to end the game
async def end_game(update: Update, context: CallbackContext, winner_id, winner_username, reason="") -> None:
    game_state = load_game_state()
    user1_score = game_state["user1"]["score"]
    user2_score = game_state["user2"]["score"]

    if reason:
        final_message = f"🏃 *{reason}*\n\n"
    else:
        final_message = ""
    
    if winner_id == game_state['user1']['id']:
        final_message += f"🎉 *O jogo terminou! {winner_username} é o grande vencedor com {user1_score} pontos!*"
        update_rankings(winner_id, game_state['user2']['id'], user1_score)
    else:
        final_message += f"🎉 *O jogo terminou! {winner_username} é o grande vencedor com {user2_score} pontos!*"
        update_rankings(winner_id, game_state['user1']['id'], user2_score)

    await context.bot.send_message(
        chat_id=game_state["group_chat_id"],
        text=final_message,
        parse_mode='Markdown'
    )
    
    # Finalize the game by resetting the game state
    game_state = {}
    save_game_state(game_state)

# Make sure to update the score after each Top Trumps game
def update_score_after_game():
    # After determining the winner and loser
    winner_id = game_state['user1']['id'] if game_state['user1']['score'] > game_state['user2']['score'] else game_state['user2']['id']
    loser_id = game_state['user1']['id'] if winner_id == game_state['user2']['id'] else game_state['user2']['id']
    
    update_rankings(winner_id, loser_id)

# Main function to start the bot
def main():
    print("Starting bot...")

    # Load the last known updated date from file
    load_last_updated_date()

    # Load chat IDs from file
    load_chat_ids()

    # Load the user IDs from file
    load_user_ids()

    # Create the application
    application = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("decks", decks))
    application.add_handler(CommandHandler("spotlight", send_spotlight_link))
    application.add_handler(CommandHandler("rank", rank))
    application.add_handler(CommandHandler("reset_rank", reset_rank))
    application.add_handler(CommandHandler("toptrumps", start_top_trumps_game))

    # Handler for welcoming new users
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))

    # Add a handler for users leaving the group
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, user_left_group))

    # Message handler for 'Galactus' keyword
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, daily_curse_by_galactus))

    # Add a handler for attribute choice in Top Trumps
    application.add_handler(CallbackQueryHandler(handle_attribute_choice))

    # Run the periodic task every 30 minutes to check for tier list updates
    job_queue = application.job_queue
    job_queue.run_repeating(check_for_update, interval=1800, first=10)

    # Start the bot
    application.run_polling()
    print("Bot is polling...")

if __name__ == '__main__':
    main()