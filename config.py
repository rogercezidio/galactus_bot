import os
import re
import logging
from pathlib import Path
from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path)

# Configuração de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Tokens e variáveis sensíveis
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GALACTUS_CHAT_ID = os.getenv("GALACTUS_CHAT_ID")

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
CARD_LIST_PATH = DATA_DIR / "card_list.json"

if TOKEN is None:
    logger.error("BOT_TOKEN não definido.")
    exit(1)

if GALACTUS_CHAT_ID is None:
    logger.error("GALACTUS_CHAT_ID não definido.")
    exit(1)

# URLs e paths
DECK_LIST_URL = "https://marvelsnapzone.com/tier-list/"
SPOTLIGHT_URL = "https://marvelsnapzone.com/spotlight-caches/"
GIF_URL = "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExc2Z4amt5dTVlYWEycmZ4bjJ1MzIwemViOTBlcGN1eXVkMXcxcXZzbiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7QL0aLRbHtAyc/giphy.gif"
WELCOME_GIF_URL = "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExZTQwb2dzejFrejhyMjc4NWh1OThtMW1vOGxvMzVwd3NtOXo2YWZhMyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xT1XGCiATaxXxW7pp6/giphy-downsized-large.gif"

# Arquivos
UPDATE_FILE_PATH = DATA_DIR / "last_update.txt"
CHAT_IDS_FILE_PATH = DATA_DIR / "chat_ids.json"
USER_IDS_FILE_PATH = DATA_DIR / "user_ids.json"
RANK_FILE = DATA_DIR / "card_votes.json"
CARDS_SENT_FILE = DATA_DIR / "cards_sent.json"

# Constantes
COOLDOWN_TIME = 60
chat_cooldowns = {}
MIN_CARTAS = 10   

# Regex para detectar "Galactus"
GALACTUS_PATTERN = re.compile(
    r"""
\b(
    g\s*[a@4áàâãäå]+\s*l\s*[a@4áàâãäåq]+\s*[cç]?\s*[t7]?\s*[uúùûü]+\s*[$sz]*
    | g[a-z@4áàâãäå]*l[a-z@4áàâãäå]*t[aoõã]*o
    | g[a4]l[a4]ctus
    | g[a4][li][a4][ck]t[uv]s
    | g[a4][li][a4][ck]t[uv]
    | g[a4]l[a4]k[t7]us
    | gaIactus
    | ギャラクタス
    | 갈러투스
    | Галактус
    | جالكتوس
    | 铁美文商者
    | गैलैक्टस
    | גלקטוס
    | galatus
    | galaquitus
    | galacta
    | 𝕓𝕊𝕇𝕊𝔼𝕊𝕌
)\b
""",
    re.VERBOSE | re.IGNORECASE,
)

# Regras do grupo
GROUP_RULES = """
Proibido:
1 - Ofensas a pessoas e/ou opiniões.
2 - Pornografias.
3 - Política, religião ou assuntos q não levem a lugar algum (direita vs. esquerda tb).
4 - Spoilers.
5 - Pirataria.
6 - Pirâmides financeiras ou afins.
"""
