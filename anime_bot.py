"""
Anime Name Corrector - Telegram Bot
"""

import os
import re
import random
import logging
from pathlib import Path

from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from thefuzz import process as fuzz_process
from ddgs import DDGS

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8282063990:AAF3YyXO6PmsL0FPQJdgAtFT25Qt-c5fEwY")
ANIME_LIST_FILE = "anime_list.txt"

FUZZY_MIN = 91

REACTION_EMOJIS = [
       "👍",  "❤", "🔥", "🥰", "👏", "😁", "🤔",
    "🤯", "😱", "😢", "🎉", "🤩", 
    "🙏", "👌", "🕊", "🥱", "😍", "🐳", "🌚", "🌭",
    "💯", "🤣", "⚡", "🍌", "🏆", "💔", "🤨", "😐",
    "🍓", "🍾", "💋", "😈", "😴", "😭", "🤓", "👻",
    "👀",  "🙈", "😇", "😨", "🤝", "🤗", "🎅",
    "💅",  "🗿", "🆒", "💘", "😘", "😎", 
]

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def load_anime_list(filepath):
    path = Path(filepath)
    if not path.exists():
        logger.warning("anime_list.txt not found. Using empty list.")
        return {}
    titles = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            original = line.strip()
            if original:
                titles[original.lower()] = original
    logger.info("Loaded %d anime titles.", len(titles))
    return titles

ANIME_LOOKUP = load_anime_list(ANIME_LIST_FILE)
ANIME_ORIGINALS = list(ANIME_LOOKUP.values())

def clean_search_title(title: str) -> str:
    """Clean google search titles like 'Death Note - Wikipedia' → 'Death Note'"""
    title = re.split(r'\s[-|(\[]\s', title)[0]
    for suffix in [" Wikipedia", " MyAnimeList", " Crunchyroll", " Fandom",
                   " AniList", " IMDb", " Netflix", " Amazon", " Wiki"]:
        title = title.replace(suffix, "")
    return title.strip()

def search_anime_online(query):
    """Search query as an anime title directly."""
    try:
        ddgs = DDGS()
        # Search the message text directly as anime title
        results = ddgs.text(f"{query} anime title", max_results=5)
        for r in results:
            raw_title = r.get("title", "").strip()
            if raw_title:
                cleaned = clean_search_title(raw_title)
                logger.info("Online result: '%s' → cleaned: '%s'", raw_title, cleaned)
                return cleaned
    except Exception as exc:
        logger.error("DuckDuckGo search failed: %s", exc)
    return None

def check_in_list(title):
    if not ANIME_ORIGINALS or not title:
        return None
    best_match, score = fuzz_process.extractOne(title, ANIME_ORIGINALS)
    logger.info("List check: '%s' → '%s' (%d%%)", title, best_match, score)
    if score >= FUZZY_MIN:
        return best_match
    return None

async def react(message, context):
    try:
        await context.bot.set_message_reaction(
            chat_id=message.chat_id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=random.choice(REACTION_EMOJIS))]
        )
    except Exception as exc:
        logger.warning("Could not set reaction: %s", exc)

async def handle_message(update, context):
    message = update.effective_message
    if not message or not message.text:
        return

    user_text = message.text.strip()
    normalized = user_text.lower()

    # Always react to every message
    await react(message, context)

    # Step 1: Exact match (100%) → react only, no reply
    if normalized in ANIME_LOOKUP:
        logger.info("Exact match: '%s'", user_text)
        return

    # Step 2: Fuzzy match (90-99%) → reply with correct name
    if ANIME_ORIGINALS:
        best_match, score = fuzz_process.extractOne(user_text, ANIME_ORIGINALS)
        logger.info("Fuzzy score for '%s': %d%% -> '%s'", user_text, score, best_match)

        if score == 100:
            logger.info("Fuzzy 100%% match: '%s' - reacting only", best_match)
            return

        if FUZZY_MIN <= score < 100:
            logger.info("Fuzzy match (%d%%): '%s' -> '%s'", score, user_text, best_match)
            await message.reply_text(f'bro please send correct anime name 👉👉 "{best_match}"')
            return

    # Step 3: Search the message as anime title → verify against txt file
    logger.info("Searching '%s' as anime title online...", user_text)
    online_title = search_anime_online(user_text)

    if online_title:
        matched = check_in_list(online_title)
        if matched:
            logger.info("Matched in list: '%s'", matched)
            await message.reply_text(f'bro please send correct anime name 👉👉 "{matched}"')
        else:
            logger.info("'%s' not found in list.", online_title)

def main():
    if BOT_TOKEN == "YOUR_NEW_TOKEN_HERE":
        raise ValueError("Please set your bot token in the script.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            handle_message,
        )
    )
    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()