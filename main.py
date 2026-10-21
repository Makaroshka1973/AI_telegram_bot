from pyrogram import Client, filters
from pyrogram.types import Message
import ollama
import re
import logging
import base64
from dotenv import load_dotenv
from os import getenv
from db import init_history_db, add_message, get_messages, init_whitelist_db, add_whitelist_ids, remove_whitelist_ids, get_whitelist_ids, memory_get_all, global_memory_get_all, add_image_to_message
from funcs import get_int_from_command, split_text, generate, get_media_type, get_utc_datetime, add_to_memory, remove_from_memory, add_to_global_memory, remove_from_global_memory

load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")
API_ID = getenv("TG_API_ID")
API_HASH = getenv("TG_API_HASH")
WHITELIST = getenv("WHITELIST").split(" ")
BASE_SYSPROMPT = [{"role": "system", "content": getenv("BASE_SYSPROMPT")}]
ADVANCED_SYSPROMPT = [{"role": "system", "content": getenv("ADVANCES_SYSPROMPT")}]
BASE_MODEL = getenv("BASE_OLLAMA_MODEL")
ADVANCED_MODEL = getenv("ADVANCED_OLLAMA_MODEL")
OWNER_ID = int(getenv("TG_OWNER_ID"))
BASE_CONTEXT_LENGTH = int(getenv("BASE_CONTEXT_LENGTH"))
ITERATION_LIMIT = int(getenv("ITERATION_LIMIT"))
TRIGGER = getenv("BOT_TRIGGER")
SESSION_NAME = getenv("SESSION_NAME")
BOT_NAME = getenv("BOT_NAME")
LOGLEVEL = getenv("LOGLEVEL").upper()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(BOT_NAME)
logger.setLevel(getattr(logging, LOGLEVEL, logging.INFO))

init_history_db()
init_whitelist_db()
add_whitelist_ids(WHITELIST)
WHITELIST = get_whitelist_ids()

app = Client(SESSION_NAME, bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)
logger.info(f"Started!")

@app.on_message(filters.command("load") & filters.reply)
def load_image_to_context(client, message):
    reply = message.reply_to_message

    if not reply.photo:
        message.reply("Эта команда работает только в ответ на сообщение с картинкой!")
        return

    logger.debug("Got /load command!")

    try:
        file = client.download_media(reply.photo.sizes[-1].file_id, in_memory=True)
        b64_image = base64.b64encode(file.getvalue()).decode('utf-8')

        add_image_to_message(reply.chat.id, reply.id, b64_image)

        message.reply("Картинка загружена!")

    except Exception as e:
        logger.error(e)
        error = f"Упс, ошибочка!\n{e}"
        message.reply(error)
        return 0

@app.on_message()
def handle_ai(client, message):
    media = get_media_type(message)
    chat_id = message.chat.id
    if message.text:
        if message.from_user:
            if message.from_user.id == OWNER_ID:
                if message.text.startswith("!enable"):
                    add_whitelist_ids([chat_id])
                    WHITELIST.append(chat_id)
                    logger.info(f"Chat {chat_id} added to whitelist")
                    message.reply("Включено!")
                elif message.text.startswith("!disable"):
                    remove_whitelist_ids([chat_id])
                    WHITELIST.remove(chat_id)
                    logger.info(f"Chat {chat_id} removed from whitelist")
                    message.reply("Выключено!")
                if message.text.startswith("!глоб-память"):
                    message.reply(f"Текущая глобальная долгосрочная память:\n{global_memory_get_all()}")
                elif message.text.startswith("!глоб-запомни "):
                    add_to_global_memory(re.sub("!глоб-запомни ", "", message.text))
                    message.reply("Добавлено в глобальную память!")
                elif message.text.startswith("!глоб-забудь "):
                    n = None
                    try:
                        n = int(re.sub("!глоб-забудь ", "", message.text))
                    except:
                                    message.reply("Произошла ошибка при попытке получить число из аргумента. Попробуйте снова")
                    if n is not None:
                        remove_from_global_memory(n)
                        message.reply("Удалено из глобальной памяти!")
        
    if chat_id in WHITELIST:
        logger.debug("Got a message")

        if message.text:
            if message.text.startswith("!память"):
                message.reply(f"Текущая долгосрочная память:\n{memory_get_all(chat_id)}")
            elif message.text.startswith("!запомни "):
                add_to_memory(chat_id, re.sub("!запомни ", "", message.text))
                message.reply("Добавлено в память!")
            elif message.text.startswith("!забудь "):
                n = None
                try:
                    n = int(re.sub("!забудь ", "", message.text))
                except:
                    message.reply("Произошла ошибка при попытке получить число из аргумента. Попробуйте снова")
                if n is not None:
                    remove_from_memory(chat_id, n)
                    message.reply("Удалено из памяти!")
        
        try:
            if message.sender_chat:
                sender = message.sender_chat.title
            elif message.from_user:
                sender = f"{message.from_user.first_name}(@{message.from_user.username})"

            header = f"# [ID: {message.id}, FROM: {sender}, DATE: {get_utc_datetime()} UTC"
            header2 = ""

            if message.reply_to_message:
                logger.debug("Message is reply")
                header += f", REPLY_TO: {message.reply_to_message.id}"
            if message.quote:
                logger.debug("Message is quote")
                header2 = f"[QUOTE: {message.quote.text}]\n"
            
            if media:
                logger.debug("Message is media")
                text = message.caption if message.caption else ""
                header += f", MEDIA: {get_media_type(message).upper()}]\n"
                add_message(message.id, chat_id, "user", header+header2+text)
                return 0
            elif not message.text:
                logger.debug("Message has not a known type")
                text = "[UNKNOWN]"
                header += "]\n"
                add_message(message.id, chat_id, "user", header+header2+text)
                return 0
            else:
                text = message.text
                header += "]\n" 
                add_message(message.id, chat_id, "user", header+header2+text)


            if message.text.startswith(TRIGGER):
                logger.debug("Bot triggered!")
                if "!думай" in message.text:
                    logger.debug("Message for advanced model")
                    IS_ADVANCED = True
                else:
                    IS_ADVANCED = False
                CONTEXT_LENGTH = get_int_from_command(message.text, "контекст")
                if not CONTEXT_LENGTH: CONTEXT_LENGTH = BASE_CONTEXT_LENGTH
                get_images = False if "!номедиа" in message.text else True
                MODEL, SYSPROMPT = (ADVANCED_MODEL, ADVANCED_SYSPROMPT) if IS_ADVANCED else (BASE_MODEL, BASE_SYSPROMPT)
                messages = get_messages(chat_id, CONTEXT_LENGTH, get_images)
                memory = [{"role": "system", "content": "Долгосрочная память этого чата:\n"+memory_get_all(chat_id)}]
                global_memory = [{"role": "system", "content": "Глобальная долгосрочная память:\n"+global_memory_get_all()}]
                response = generate(MODEL, SYSPROMPT+global_memory+memory+messages, ITERATION_LIMIT)

                if response:
                    msgs = split_text(response["content"], 4096)
                    for msg in msgs:
                        message.reply(msg)

                    if response["content"].strip() != "":
                        add_message(message.id, chat_id, response["role"], response["content"])
                        logger.debug("Answered!")
                else:
                    add_message(message.id, chat_id, "assistant", "Был превышен лимит итераций. Пожалуйста, попробуйте снова.")
                    message.reply("Был превышен лимит итераций. Пожалуйста, попробуйте снова.")
                    logger.warning("The iteration limit has been exceeded!")
                
                return 0

        except Exception as e:
            logger.error(e)
            error = f"Упс, ошибочка!\n{e}"
            add_message(message.id, chat_id, "assistant", error)
            message.reply(error)
            return 0

app.run()
