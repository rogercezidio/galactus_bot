from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import DECK_LIST_URL, logger
import re, logging, requests
from bs4 import BeautifulSoup
from typing import Optional

logger = logging.getLogger(__name__)
UA = {"User-Agent": "Mozilla/5.0 (compatible; SnapBot/1.0)"}

_DATE_RE = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},\s+\d{4}"
)

TIER_EMOJIS = {
    "Tier S": "👑",
    "Tier 1": "1️⃣",
    "Tier 2": "2️⃣",
    "Tier 3": "3️⃣",
    "Trending": "🔥",
}
DEFAULT_TIER_EMOJI = "⭐"


def get_decks_keyboard():
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        driver.get(DECK_LIST_URL)

        table = driver.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]  

        keyboard = []

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 2:
                continue

            tier_text = cols[0].text.strip()
            tier_emoji = TIER_EMOJIS.get(tier_text, DEFAULT_TIER_EMOJI)

            link_tag = cols[1].find_element(By.TAG_NAME, "a")
            deck_name = link_tag.text.strip()
            deck_link = link_tag.get_attribute("href")

            button_display_text = f"{tier_emoji} {deck_name}"

            html_raw = cols[1].get_attribute("innerHTML")
            split_parts = html_raw.split("<br>")

            if len(split_parts) > 1:
                from bs4 import BeautifulSoup

                post_br_html = split_parts[1]
                post_text = BeautifulSoup(post_br_html, "html.parser").text.strip()
                if "/" in post_text:
                    cube_info, win_rate_info = [p.strip() for p in post_text.split("/", 1)]
                    cube_value = cube_info.split(" ", 1)[0]
                    win_rate_value = win_rate_info.split(" ", 1)[0]
                    button_display_text += f" | 🧊 {cube_value} | 📈 {win_rate_value}"
                else:
                    button_display_text += f" | 📊 {post_text.replace('/', '|')}"

            keyboard.append([InlineKeyboardButton(button_display_text, url=deck_link)])

        driver.quit()
        return InlineKeyboardMarkup(keyboard)

    except Exception as e:
        logger.error(f"Erro ao montar teclado de decks com Selenium: {e}")
        return None


def _extract_date_from_html(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")

    fig = soup.select_one("figure.wp-block-table figcaption")
    if fig:
        m = _DATE_RE.search(fig.get_text(" ", strip=True))
        if m:
            return m.group(0)

    m = re.search(r"Updated:\s*" + _DATE_RE.pattern, soup.get_text(" ", strip=True))
    if m:
        return _DATE_RE.search(m.group(0)).group(0)

    return None


def fetch_updated_date_fast() -> Optional[str]:
    """Devolve a data de atualização visível; fallback para Last-Modified."""
    try:
        resp = requests.get(DECK_LIST_URL, headers=UA, timeout=8)
        resp.raise_for_status()
    except Exception as exc:
        log.error("GET %s falhou: %s", DECK_LIST_URL, exc)
        return None

    date_html = _extract_date_from_html(resp.text)
    if date_html:
        return date_html
    return resp.headers.get("Last-Modified")