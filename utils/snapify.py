import os, io, random, base64, logging, asyncio, aiofiles
from openai import OpenAI
from utils.helpers import get_user_profile_photo_async, encode_image_async

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
log    = logging.getLogger(__name__)

STATS = [(1,1), (2,3), (3,5), (5,7), (6,9)]   # custo × poder

async def generate_snap_card_with_user_photo(bot, user):
    # 1 ▸ baixa foto do perfil
    photo_path = await get_user_profile_photo_async(user.id, bot)
    if not photo_path:
        raise RuntimeError("Usuário sem foto de perfil.")

    b64_photo = await encode_image_async(photo_path)
    if not b64_photo:
        raise RuntimeError("Falha ao codificar foto.")

    cost, power = random.choice(STATS)
    title = user.first_name.upper()

    # 2 ▸ prompt + imagem embutida
    prompt = (
        f"Create a Marvel Snap trading card called {title}. "
        f"Use the supplied photo as main art, add a dynamic comic-book frame, "
        f"cost {cost} in the blue energy circle (top-left) and power {power} in the orange hex (bottom-right). "
        f"Vibrant colours, clean edges, no extra text."
    )

    response = client.responses.create(
        model="gpt-4.1",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text",  "text": prompt},
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{b64_photo}",
                },
            ],
        }],
        tools=[{"type": "image_generation"}],
    )

    # 3 ▸ extrai o primeiro bloco de imagem gerada
    img_b64 = next(
        (out.result for out in response.output if out.type == "image_generation_call"),
        None,
    )
    if not img_b64:
        raise RuntimeError("A geração de imagem falhou.")

    img_bytes = io.BytesIO(base64.b64decode(img_b64))
    img_bytes.name = "snap_card.jpg"

    caption = f"*{title}*\n💰 {cost} | 💥 {power}"
    return img_bytes, caption
