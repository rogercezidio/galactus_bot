import json, re
from config import CARD_LIST_PATH, _EXCLUDED
from bs4 import BeautifulSoup
import requests
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def get_card_info(card_name):
    base_url = "https://marvelsnapzone.com/cards/"
    card_slug = card_name.lower().replace(" ", "-")
    url = f"{base_url}{card_slug}/"

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return f"Erro ao acessar a página da carta: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    name_tag = soup.select_one("h1.entry-title")
    name = name_tag.get_text(strip=True) if name_tag else card_name.title()

    img_tag = soup.select_one("div.cardimage div.front img")
    img_url = img_tag["src"] if img_tag and img_tag.get("src") else None

    description_tag = soup.select_one("div.cardimage div.front div.info p")
    description = description_tag.get_text(strip=True) if description_tag else "Descrição não encontrada."

    decks_link_tag = soup.select_one("a.btn.icon.deck-list")
    decks_link = decks_link_tag["href"] if decks_link_tag and decks_link_tag.get("href") else f"https://marvelsnapzone.com/decks/{card_slug}"

    card_url = url

    if img_url:
        return {
            "name": name,
            "slug": card_slug,
            "url": card_url,
            "image": img_url,
            "description": description,
            "decks_url": decks_link
        }
    else:
        return f"Carta '{card_name}' não encontrada ou sem imagem disponível."
        

def format_card_message(card_data):
    return (
        f"**{card_data['name']}**\n\n"
        f"📝 {card_data['description']}\n\n"
        f"[🔍 Ver detalhes]({card_data['url']}) | [🧩 Ver decks]({card_data['decks_url']})"
    )


def get_all_cards_with_tags() -> List[Dict[str, str]]:
    url = "https://marvelsnapzone.com/cards/"
    driver = webdriver.Chrome(options=_chrome_opts())
    try:
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.simple-card div.cardname"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
    finally:
        driver.quit()

    cards = []
    for anchor in soup.select("a.simple-card"):
        name_div = anchor.select_one("div.cardname")
        if not name_div:
            continue
        name = name_div.get_text(strip=True)

        tag_span = anchor.select_one("div.tags span.tag-item")
        tag_texts = [t.get_text(strip=True) for t in anchor.select("div.tags span.tag-item")]
        tag_texts = [" ".join(re.split(r"\s+", t)) for t in tag_texts if t.strip()]
        tag = " | ".join(tag_texts) if tag_texts else "Unknown"

        cards.append({"name": name, "tag": tag})

    return cards


def save_cards_to_file(cards: List[Dict[str, str]], path: str):
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(cards, fp, ensure_ascii=False, indent=2)


def update_card_list():
    print("🔄 Baixando grid de cartas (grid mode)…")
    cards = get_all_cards_with_tags()
    if not cards:
        print("❌ Nada encontrado – abortando.")
        return
    save_cards_to_file(cards, CARD_LIST_PATH)
    print(f"✅ {len(cards)} cartas (com tag) salvas em {CARD_LIST_PATH}")


def _generate_card_list_if_missing() -> None:
    if CARD_LIST_PATH.exists():
        return
    logger.warning("%s não encontrado – gerando via scraper…", CARD_LIST_PATH)
    try:
        from utils.cards import update_card_list
        update_card_list()
    except Exception as exc:
        logger.error("Falha ao gerar card_list.json automaticamente: %s", exc)
        raise FileNotFoundError(
            f"{CARD_LIST_PATH} não encontrado e o scraper falhou."
        ) from exc

def load_playable_card_names() -> List[str]:
    _generate_card_list_if_missing()
    with CARD_LIST_PATH.open(encoding="utf-8") as fp:
        data = json.load(fp)

    return [
        c["name"]
        for c in data
        if c.get("tag") and c["tag"].strip().lower() not in _EXCLUDED
    ]

CARDS_NAMES = load_playable_card_names()
