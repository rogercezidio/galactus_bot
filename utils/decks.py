import requests
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import DECK_LIST_URL, logger

def fetch_updated_date():
    try:
        response = requests.get(DECK_LIST_URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        figcaption = soup.find('figcaption')

        if figcaption and 'Updated:' in figcaption.get_text():
            return figcaption.get_text(strip=True).split("Updated:")[1].strip()
        logger.info("Elemento de data não encontrado na página.")
    except Exception as e:
        logger.error(f"Erro ao buscar data de atualização: {e}")
    return None

def get_decks_keyboard():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(DECK_LIST_URL, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table')
        if not table:
            return None

        keyboard = []
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                tier = cols[0].text.strip()
                deck_name = cols[1].text.strip()
                link_tag = cols[1].find('a')
                link = link_tag['href'] if link_tag else None
                if link:
                    keyboard.append([
                        InlineKeyboardButton(f"{tier}: {deck_name}", url=link)
                    ])

        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        logger.error(f"Erro ao montar teclado de decks: {e}")
        return None
