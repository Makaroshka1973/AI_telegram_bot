from pyrogram import Client, filters
import ollama
import re
import logging
from dotenv import load_dotenv
from os import getenv
from db import init_history_db, add_message, get_messages, init_whitelist_db, add_whitelist_ids, remove_whitelist_ids, get_whitelist_ids, memory_get_all
from funcs import get_int_from_command, split_text, generate, get_media_type, get_utc_datetime, add_to_memory, remove_from_memory

load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")
API_ID = getenv("TG_API_ID")
API_HASH = getenv("TG_API_HASH")
WHITELIST = getenv("WHITELIST").split(" ")
BASE_SYSPROMPT = [{"role": "system", "content": getenv("BASE_SYSPROMPT")}]
ADVANCED_SYSPROMPT = [{"role": "system", "content": getenv("ADVANCES_SYSPROMPT")}]
MEMORY_SYSPROMPT = getenv("MEMORY_SYSPROMPT")
BASE_MODEL = getenv("BASE_OLLAMA_MODEL")
ADVANCED_MODEL = getenv("ADVANCED_OLLAMA_MODEL")
OWNER_ID = int(getenv("TG_OWNER_ID"))
BASE_CONTEXT_LENGTH = int(getenv("BASE_CONTEXT_LENGTH"))
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

@app.on_message()
def handle_ai(client, message):
    media = get_media_type(message)
    chat_id = message.chat.id
    if message.text:
        if message.text.startswith("!enable") and message.from_user.id == OWNER_ID:
            add_whitelist_ids([chat_id])
            WHITELIST.append(chat_id)
            logger.info(f"Chat {chat_id} added to whitelist")
            message.reply("Включено!")
        elif message.text.startswith("!disable") and message.from_user.id == OWNER_ID:
            remove_whitelist_ids([chat_id])
            WHITELIST.remove(chat_id)
            logger.info(f"Chat {chat_id} removed from whitelist")
            message.reply("Выключено!")
        
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
                add_message(chat_id, "user", header+header2+text)
                return 0
            elif not message.text:
                logger.debug("Message has not a known type")
                text = "[UNKNOWN]"
                header += "]\n"
                add_message(chat_id, "user", header+header2+text)
                return 0
            else:
                text = message.text
                header += "]\n" 
                add_message(chat_id, "user", header+header2+text)


            if message.text.startswith(TRIGGER):
                logger.debug("Bot triggered!")
                if "!думай" in message.text:
                    logger.debug("Message for advanced model")
                    IS_ADVANCED = True
                else:
                    IS_ADVANCED = False
                CONTEXT_LENGTH = get_int_from_command(message.text, "контекст")
                if not CONTEXT_LENGTH: CONTEXT_LENGTH = BASE_CONTEXT_LENGTH
                MODEL, SYSPROMPT = (ADVANCED_MODEL, ADVANCED_SYSPROMPT) if IS_ADVANCED else (BASE_MODEL, BASE_SYSPROMPT)
                messages = get_messages(chat_id, CONTEXT_LENGTH)
                memory = [{"role": "system", "content": "Долгосрочная память этого чата:\n"+memory_get_all(chat_id)}]
                response = generate(MODEL, SYSPROMPT+memory+messages)

                msgs = split_text(response["content"], 4096)
                for msg in msgs:
                    message.reply(msg)

                if response["content"].strip() != "":
                    add_message(chat_id, response["role"], response["content"])
                    logger.debug("Answered!")
                
                return 0

        except Exception as e:
            logger.error(e)
            error = f"Упс, ошибочка!\n{e}"
            add_message(chat_id, "assistant", error)
            message.reply(error)
            return 0

app.run()
