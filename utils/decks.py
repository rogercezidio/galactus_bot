import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import DECK_LIST_URL, logger

TIER_EMOJIS = {
    "Tier S": "👑",  # Tier S
    "Tier 1": "1️⃣",  # Tier 1 - Número Um
    "Tier 2": "2️⃣",  # Tier 2 - Número Dois
    "Tier 3": "3️⃣",  # Tier 3 - Número Três
    "Trending": "🔥",  # Decks em ascensão / "fora do radar"
    # Adicione outros tiers e seus emojis aqui se o site os usar
}
DEFAULT_TIER_EMOJI = "⭐"  # Emoji padrão se o tier não for encontrado


def fetch_updated_date():
    try:
        response = requests.get(DECK_LIST_URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        figcaption = soup.find("figcaption")

        if figcaption and "Updated:" in figcaption.get_text():
            return figcaption.get_text(strip=True).split("Updated:")[1].strip()
        logger.info("Elemento de data não encontrado na página.")
    except Exception as e:
        logger.error(f"Erro ao buscar data de atualização: {e}")
    return None


def get_decks_keyboard():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(DECK_LIST_URL, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table")
        if not table:
            return None

        keyboard = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                tier_text = cols[0].text.strip()
                tier_emoji = TIER_EMOJIS.get(tier_text, DEFAULT_TIER_EMOJI)
                # tier_display agora será apenas o emoji
                tier_display = tier_emoji
                deck_cell = cols[1]

                link_tag = deck_cell.find("a")

                if link_tag and link_tag.has_attr("href"):
                    deck_name_from_a = link_tag.text.strip()
                    deck_link = link_tag["href"]

                    # Formatar para linha única, pois o Telegram não suporta múltiplas linhas em botões de forma confiável.
                    button_display_text = f"{tier_display} {deck_name_from_a}"

                    # Encontrar o texto após a tag <br>
                    br_tag = deck_cell.find("br")
                    if br_tag and br_tag.next_sibling:
                        # next_sibling pode ser um NavigableString ou outro Tag
                        if isinstance(br_tag.next_sibling, NavigableString):
                            additional_info_str = br_tag.next_sibling.strip()
                            if (
                                additional_info_str
                            ):  # Certifica-se de que não está vazio após o strip
                                parts = additional_info_str.split(
                                    "/", 1
                                )  # Divide apenas na primeira '/'

                                if len(parts) == 2:
                                    cube_info_raw = parts[0].strip()
                                    win_rate_info_raw = parts[1].strip()

                                    # Extrai apenas o valor numérico/percentual (geralmente a primeira parte antes de um espaço)
                                    cube_value = (
                                        cube_info_raw.split(" ", 1)[0]
                                        if cube_info_raw
                                        else ""
                                    )
                                    win_rate_value = (
                                        win_rate_info_raw.split(" ", 1)[0]
                                        if win_rate_info_raw
                                        else ""
                                    )

                                    cube_emoji = "🧊"
                                    win_rate_emoji = "📈"
                                    button_display_text += f" | {cube_emoji} {cube_value} | {win_rate_emoji} {win_rate_value}"
                                else:
                                    # Fallback se o formato não for "Algo / Algo mais"
                                    # Substitui qualquer '/' restante por '|' e usa um emoji genérico
                                    processed_info = additional_info_str.replace(
                                        "/", " | "
                                    )
                                    generic_stats_emoji = "📊"
                                    button_display_text += (
                                        f" | {generic_stats_emoji} {processed_info}"
                                    )

                    keyboard.append(
                        [InlineKeyboardButton(button_display_text, url=deck_link)]
                    )

        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        logger.error(f"Erro ao montar teclado de decks: {e}")
        return None
