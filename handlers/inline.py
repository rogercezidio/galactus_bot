from telegram import (
    InlineQueryResultPhoto,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.ext import ContextTypes
from utils.cards import get_card_variants


async def inline_query_handler(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        return

    variants = get_card_variants(query)
    results = []
    for idx, variant in enumerate(variants):
        image_url = variant.get("image_url")
        if image_url:
            results.append(
                InlineQueryResultPhoto(
                    id=f"{query}_{idx}",
                    photo_url=image_url,
                    thumb_url=image_url,
                    title=variant["title"],
                    caption=variant.get("caption", variant["title"]),
                )
            )
        else:
            results.append(
                InlineQueryResultArticle(
                    id=f"{query}_{idx}",
                    title=variant["title"],
                    input_message_content=InputTextMessageContent(
                        variant.get("caption", variant["title"])
                    ),
                )
            )
    await update.inline_query.answer(results, cache_time=1, is_personal=True)
