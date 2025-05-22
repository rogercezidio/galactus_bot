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

    img_tag = soup.select_one("div.cardimage div.front img")
    img_url = img_tag["src"] if img_tag and img_tag.get("src") else None

    description_tag = soup.select_one("div.cardimage div.front div.info p")
    description = (
        description_tag.get_text(strip=True)
        if description_tag
        else "Descrição não encontrada."
    )

    if img_url:
        return {
            "name": card_name.title(),
            "url": url,
            "image": img_url,
            "description": description,
        }
    else:
        return f"Carta '{card_name}' não encontrada."


def format_card_message(card_data):
    return f"**{card_data['name']}**\n{card_data['description']}\n[Ver mais]({card_data['url']})"
