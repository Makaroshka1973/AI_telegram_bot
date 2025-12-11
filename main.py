from pyrogram import Client, filters
import ollama
import re
from dotenv import load_dotenv
from os import getenv
from db import init_history_db, add_message, get_messages, init_whitelist_db, add_whitelist_ids, remove_whitelist_ids, get_whitelist_ids

load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")
API_ID = getenv("TG_API_ID")
API_HASH = getenv("TG_API_HASH")
SYSPROMPT = [{"role": "system", "content": getenv("SYSPROMPT")}]
WHITELIST = getenv("WHITELIST").split(" ")
BASE_MODEL = getenv("BASE_OLLAMA_MODEL")
OWNER_ID = int(getenv("TG_OWNER_ID"))
BASE_CONTEXT_LENGTH = int(getenv("BASE_CONTEXT_LENGTH"))
TRIGGER = getenv("BOT_TRIGGER")
SESSION_NAME = getenv("SESSION_NAME")
BOT_NAME = getenv("BOT_NAME")

init_history_db()
init_whitelist_db()
add_whitelist_ids(WHITELIST)
WHITELIST = get_whitelist_ids()

def get_int_from_command(message: str, word: str):
    pattern = rf'!{word}=(\d+)'
    m = re.search(pattern, message)
    if m: num = int(m.group(1))
    else: num = None
    return num

def split_text(text: str, max_length: int):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

def generate(model, messages):
    response = ollama.chat(
        model=model,
        messages=messages
    )
    return response["message"]

app = Client(SESSION_NAME, bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)
print(f"{BOT_NAME} started!")

@app.on_message()
def handle_ai(client, message):
    chat_id = message.chat.id
    if message.text.startswith("!enable") and message.from_user.id == OWNER_ID:
        add_whitelist_ids([chat_id])
        WHITELIST.append(chat_id)
        message.reply("Включено!")
    elif message.text.startswith("!disable") and message.from_user.id == OWNER_ID:
        remove_whitelist_ids([chat_id])
        WHITELIST.remove(chat_id)
        message.reply("Выключено!")
        
    if chat_id in WHITELIST:
        try:
            if message.sender_chat:
                sender = message.sender_chat.title
            elif message.from_user:
                sender = message.from_user.first_name

            if message.media:
                add_message(chat_id, "user", f"[FROM: {sender}] [MEDIA]")
                return 0
            elif not message.text:
                add_message(chat_id, "user", f"[FROM: {sender}] [UNKNOWN]")
                return 0
            else:
                add_message(chat_id, "user", f"[FROM: {sender}] {message.text}")


            if message.text.startswith(TRIGGER):
                CONTEXT_LENGTH = get_int_from_command(message.text, "контекст")
                if not CONTEXT_LENGTH: CONTEXT_LENGTH = BASE_CONTEXT_LENGTH

                response = generate(BASE_MODEL, SYSPROMPT+get_messages(chat_id, CONTEXT_LENGTH))
                add_message(chat_id, response["role"], response["content"])

                messages = split_text(response["content"], 4096)
                for msg in messages:
                    message.reply(msg)
                return 0

        except Exception as e:
            error = f"Упс, ошибочка!\n{e}"
            add_message(chat_id, "assistant", error)
            message.reply(error)
            return 0

app.run()
