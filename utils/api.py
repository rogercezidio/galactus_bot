import os
import base64
import logging
import requests
from openai import AsyncOpenAI
from config import OPENAI_API_KEY
from utils.helpers import encode_image_async

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def generate_galactus_welcome(name: str) -> str:
    prompt = f"Galactus vai dar boas-vindas ao humano {name}. Seja poderoso e amigável."
    try:
        res = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você é Galactus, o Devorador de Mundos.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return res.choices[0].message.content
    except Exception as e:
        logging.error(f"Erro na mensagem de boas-vindas: {e}")
        return f"{name}, Galactus te notou. Bem-vindo, humano insignificante!"


async def generate_galactus_farewell(name: str) -> str:
    prompt = f"Galactus vai se despedir de {name} com sarcasmo e desdém."
    try:
        res = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você é Galactus, o Devorador de Mundos.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return res.choices[0].message.content
    except Exception as e:
        logging.error(f"Erro na despedida: {e}")
        return f"{name}, você acha que pode escapar de Galactus? Insignificante!"


async def generate_galactus_roast(name: str, photo_path: str) -> str:
    img_b64 = await encode_image_async(photo_path)

    if not img_b64:
        return f"{name}, sua imagem é tão irrelevante que nem Galactus se importa."

    try:
        vision_payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Descreva esta imagem em português."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 300,
        }

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        vision_resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=vision_payload,
        )
        vision_resp.raise_for_status()
        desc = vision_resp.json()["choices"][0]["message"]["content"]

        roast_prompt = (
            f"Galactus está prestes a humilhar um humano chamado {name}. Aqui está a descrição da imagem de perfil desse usuário: {desc}. Escreva um insulto humilhante, sarcástico e devastador baseado nessa descrição."
        )

        res = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Você é Galactus, o devorador de mundos. Humilhe este humano de forma curta e grossa como só Galactus pode, mencionando seu nome e usando a imagem descrita."},
                {"role": "user", "content": roast_prompt}
            ],
        )
        return res.choices[0].message.content
    except Exception as e:
        logging.error(f"Erro no roast: {e}")
        return f"{name}, até Galactus não consegue te zoar. Insignificante!"
