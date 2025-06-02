import json, re
from config import CARD_LIST_PATH
from bs4 import BeautifulSoup
import requests
from typing import List, Dict
from pathlib import Path
import logging
import random, datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)


def _chrome_opts() -> Options:
    """Configurações padrão para rodar Chrome em headless dentro do container."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return opts


def _url_is_image(url: str, timeout=5) -> bool:
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        return r.ok and r.headers.get("content-type", "").startswith("image/")
    except Exception:
        return False


def get_card_info(name: str) -> Dict:
    slug = name.lower().replace(" ", "-")
    url = f"https://marvelsnapzone.com/cards/{slug}/"
    decks_url = f"https://marvelsnapzone.com/decks/{slug}"

    driver = webdriver.Chrome(options=_chrome_opts())

    try:
        driver.get(url)

        if "404" in driver.title or "Página não encontrada" in driver.page_source:
            return {
                "error": f"Carta '{name}' não encontrada.",
                "slug": slug,
                "url": url,
            }

        h1 = (
            WebDriverWait(driver, 5)
            .until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main.site-main h1"))
            )
            .text.strip()
        )

        img_elems = driver.find_elements(By.CSS_SELECTOR, "div.cardimage div.front img")
        image_url = img_elems[0].get_attribute("src") if img_elems else None
        if image_url and not _url_is_image(image_url):
            image_url = None

        desc_elems = driver.find_elements(
            By.CSS_SELECTOR, "div.cardimage div.front div.info div"
        )
        description = (
            desc_elems[0].text.strip() if desc_elems else "Descrição não encontrada."
        )

        cost = driver.find_elements(By.CSS_SELECTOR, "div.block .cost")
        power = driver.find_elements(By.CSS_SELECTOR, "div.block .power span")
        cost = cost[0].text.strip() if cost else "??"
        power = power[0].text.strip() if power else "??"

        tag_elems = driver.find_elements(By.CSS_SELECTOR, "div.tags a")
        tags: List[str] = [t.text.strip() for t in tag_elems if t.text.strip()]
        series = driver.find_elements(
            By.XPATH, "//div[div[text()='Source']]/div[@class='info']"
        )
        if series:
            tags.append(series[0].text.strip())

        return {
            "name": h1,
            "slug": slug,
            "url": url,
            "decks_url": decks_url,
            "image": image_url,
            "description": description,
            "cost": cost,
            "power": power,
            "tags": tags,
        }

    except TimeoutException:
        return {
            "error": f"Carta '{name}' não carregou a tempo.",
            "slug": slug,
            "url": url,
        }
    except Exception as exc:
        return {"error": f"Erro inesperado: {exc}", "slug": slug, "url": url}
    finally:
        driver.quit()


def format_card_message(card_data):
    base = f"**{card_data['name']}**\n\n"
    stats = f"💰 Custo: {card_data.get('cost', '??')} | 💥 Poder: {card_data.get('power', '??')}\n\n"
    desc = f"📝 {card_data['description']}\n\n"
    tags = f"🏷️ {' | '.join(card_data['tags'])}\n\n" if card_data["tags"] else ""
    links = f"[🔍 Ver detalhes]({card_data['url']}) | [🧩 Ver decks]({card_data['decks_url']})"
    return base + stats + tags + desc + links


def get_all_cards_with_tags() -> List[Dict[str, str]]:
    url = "https://marvelsnapzone.com/cards/"
    driver = webdriver.Chrome(options=_chrome_opts())
    try:
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a.simple-card div.cardname")
            )
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

        tag_texts = [
            t.get_text(strip=True) for t in anchor.select("div.tags span.tag-item")
        ]
        tag_texts = [" ".join(re.split(r"\s+", t)) for t in tag_texts if t.strip()]
        tag = " | ".join(tag_texts) if tag_texts else "Unknown"

        cards.append({"name": name, "tag": tag})

    return cards


def salvar_cards_em_arquivo(cards: List[Dict[str, str]], path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(cards, fp, ensure_ascii=False, indent=2)


def atualizar_lista_de_cartas():
    print("🔄 Baixando grid de cartas (grid mode)…")
    cards = get_all_cards_with_tags()
    if not cards:
        print("❌ Nada encontrado – abortando.")
        return
    salvar_cards_em_arquivo(cards, CARD_LIST_PATH)
    print(f"✅ {len(cards)} cartas (com tag) salvas em {CARD_LIST_PATH}")


def _today_key() -> str:
    return datetime.date.today().isoformat()


def pick_card_without_repetition(bot_data: dict, card_names: list[str]) -> str:
    """
    Escolhe uma carta aleatória. Garante que cada carta seja usada no máximo 1× por dia.
    Reinicia o ciclo se esgotar todas.
    """
    used_today: set[str] = bot_data.setdefault("cards_sent", {}).setdefault(
        _today_key(), set()
    )
    remaining = [c for c in card_names if c not in used_today]
    if not remaining:
        used_today.clear()
        remaining = card_names
    card = random.choice(remaining)
    used_today.add(card)
    return card


_EXCLUDED = {"none", "unreleased"}


def _generate_card_list_if_missing() -> None:
    if CARD_LIST_PATH.exists():
        return
    logger.warning("%s não encontrado – gerando via scraper…", CARD_LIST_PATH)
    try:
        from utils.cards import atualizar_lista_de_cartas

        atualizar_lista_de_cartas()
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


def get_card_variants(card_name: str):
    import json
    from config import CARD_LIST_PATH

    path = CARD_LIST_PATH
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        cards = json.load(f)
    results = []
    card_name_lower = card_name.lower().strip()
    for card in cards:
        if card_name_lower in card.get("name", "").lower():
            variants = card.get("variants", [])
            base = {
                "title": card["name"],
                "image_url": card.get("image_url"),  # agora usa URL pública
                "caption": card.get("description", card["name"]),
            }
            results.append(base)
            for v in variants:
                v = v.copy()
                if v.get("image_url"):
                    v["image_url"] = v["image_url"]
                results.append(v)
    return results
