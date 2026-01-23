import re
import json
import ollama
import datetime
from db import memory_add, memory_remove, memory_get, global_memory_add, global_memory_remove, global_memory_get

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

def get_media_type(message):
    media_type = None
    if message.media:
        if message.photo: media_type = "photo"
        elif message.video: media_type = "video"
        elif message.animation: media_type = "gif"
        elif message.sticker: media_type = "sticker"
        elif message.audio: media_type = "audio"
        elif message.voice: media_type = "voice" 
        elif message.document: media_type = "document"
        else: media_type = "unknown"
    return media_type

def get_utc_datetime():
    return datetime.datetime.utcnow().replace(microsecond=0)

def add_to_memory(chat_id: int, fact: str):
    memory_add(chat_id, [fact])

def remove_from_memory(chat_id: int, n: int):
    fact = memory_get(chat_id, n)
    memory_remove(chat_id, [fact])

def add_to_global_memory(fact: str):
    global_memory_add([fact])

def remove_from_global_memory(n: int):
    fact = global_memory_get(n)
    global_memory_remove([fact])
