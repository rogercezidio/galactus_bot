import requests
from bs4 import BeautifulSoup

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

    # Nome da carta
    name_tag = soup.select_one("h1.entry-title")
    name = name_tag.get_text(strip=True) if name_tag else card_name.title()

    # Imagem
    img_tag = soup.select_one("div.cardimage div.front img")
    img_url = img_tag["src"] if img_tag and img_tag.get("src") else None

    # Habilidade / descrição
    description_tag = soup.select_one("div.cardimage div.front div.info p")
    description = description_tag.get_text(strip=True) if description_tag else "Descrição não encontrada."

    # Link de decks
    decks_link_tag = soup.select_one("a.btn.icon.deck-list")
    decks_link = decks_link_tag["href"] if decks_link_tag and decks_link_tag.get("href") else f"https://marvelsnapzone.com/decks/{card_slug}"

    # Link de detalhes
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
        f"**{card_data['name']}**\n"
        f"📝 {card_data['description']}\n\n"
        f"[🔍 Ver detalhes]({card_data['url']}) | [🧩 Ver decks]({card_data['decks_url']})"
    )
