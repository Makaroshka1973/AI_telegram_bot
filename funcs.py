import re
import json
import ollama
import datetime
from ddgs import DDGS
from httpx import get
from db import memory_add, memory_remove, memory_get, global_memory_add, global_memory_remove, global_memory_get


def ddgs_search(query: str, max_results=5):
    with DDGS() as ddgs:
        results = [r for r in ddgs.text(query, max_results=max_results)]
        return str(results)

def web_get(url):
    return get(url).text

ai_tools = {"ddgs_search": ddgs_search, "web_get": web_get}
tools_defs = [
    {
        'type': 'function',
        'function': {
            'name': 'ddgs_search',
            'description': 'Search of actual information in DuckDuckGo',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Search query'
                    },
                    'max_results': {
                        'type': 'integer',
                        'description': 'Maximum number of results'
                    }
                },
                'required': ['query']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'web_get',
            'description': 'Get a raw text of the page',
            'parameters': {
                'type': 'object',
                'properties': {
                    'url': {
                        'type': 'string',
                        'description': 'URL of the page'
                    }
                },
                'required': ['url']
            }
        }
    }
]

def get_int_from_command(message: str, word: str):
    pattern = rf'!{word}=(\d+)'
    m = re.search(pattern, message)
    if m: num = int(m.group(1))
    else: num = None
    return num

def split_text(text: str, max_length: int):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

def generate(model, messages, max_iterations=5):
    iterations = 0
    while iterations < max_iterations:
        response = ollama.chat(
            model=model,
            messages=messages,
            tools=tools_defs
        )
        if response.message.tool_calls:
            print(response.message.tool_calls)
            for tool_call in response.message.tool_calls:
                function = ai_tools.get(tool_call.function.name)
                if function:
                    args = tool_call.function.arguments
                    result = function(**args)
                    print(result)
                    messages.append({"role": "user", "content": f"Result of tool {tool_call.function.name}: {result}"})
        else:
            break
        iterations += 1
    if iterations < max_iterations:
        return response["message"]
    else:
        return None

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

