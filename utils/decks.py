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
        resp = requests.get(DECK_LIST_URL, headers=UA, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        table = soup.find("table")
        if not table:
            logger.error("Tabela de decks não encontrada")
            return None

        keyboard = []

        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            tier_text = cols[0].get_text(strip=True)
            tier_emoji = TIER_EMOJIS.get(tier_text, DEFAULT_TIER_EMOJI)

            link_tag = cols[1].find("a", href=True)
            if not link_tag:
                continue
            deck_name = link_tag.get_text(strip=True)
            deck_link = link_tag["href"]

            button_display_text = f"{tier_emoji} {deck_name}"

            post_text = ""
            br = cols[1].find("br")
            if br:
                nxt = br.next_sibling
                while nxt and ((getattr(nxt, "name", None) == "br") or (isinstance(nxt, str) and not nxt.strip())):
                    nxt = nxt.next_sibling
                if nxt:
                    if hasattr(nxt, "get_text"):
                        post_text = nxt.get_text(" ", strip=True)
                    else:
                        post_text = str(nxt).strip()
            if not post_text:
                texts = list(cols[1].stripped_strings)
                if len(texts) > 1:
                    post_text = texts[1]

            if post_text:
                if "/" in post_text:
                    cube_info, win_rate_info = [p.strip() for p in post_text.split("/", 1)]
                    cube_value = cube_info.split(" ", 1)[0]
                    win_rate_value = win_rate_info.split(" ", 1)[0]
                    button_display_text += f" | 🧊 {cube_value} | 📈 {win_rate_value}"
                else:
                    button_display_text += f" | 📊 {post_text.replace('/', '|')}"

            keyboard.append([InlineKeyboardButton(button_display_text, url=deck_link)])

        return InlineKeyboardMarkup(keyboard)

    except Exception as e:
        logger.error(f"Erro ao montar teclado de decks: {e}")
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
        logger.error("GET %s falhou: %s", DECK_LIST_URL, exc)
        return None

    date_html = _extract_date_from_html(resp.text)
    if date_html:
        return date_html
    return resp.headers.get("Last-Modified")