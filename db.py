import sqlite3
from datetime import datetime

def init_history_db():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    
    # creating table
    c.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        UNIQUE(chat_id, content)
    )
    ''')

    # indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_chat_id ON messages (chat_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON messages (timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_memory_chat_id ON memory (chat_id)')

    conn.commit()
    conn.close()

def add_message(chat_id, role, content):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute('''
    INSERT INTO messages (chat_id, role, content)
    VALUES (?, ?, ?)
    ''', (chat_id, role, content))

    conn.commit()
    conn.close()

def get_messages(chat_id, context_length):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()

    c.execute('''
    SELECT role, content 
    FROM messages 
    WHERE chat_id = ? 
    ORDER BY timestamp DESC 
    LIMIT ?
    ''', (chat_id, context_length))

    messages = c.fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in reversed(messages)]

def init_whitelist_db():
    conn = sqlite3.connect("whitelist.db")
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS ids (
            id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit
    conn.close()

def add_whitelist_ids(ids: list):
    conn = sqlite3.connect("whitelist.db")
    c = conn.cursor()

    c.executemany("INSERT OR IGNORE INTO ids (id) VALUES (?)",
                  [(value,) for value in ids])
    conn.commit()
    conn.close()

def remove_whitelist_ids(ids: list):
    conn = sqlite3.connect("whitelist.db")
    c = conn.cursor()

    c.executemany("DELETE FROM ids WHERE id = ?",
                  [(value,) for value in ids])
    conn.commit()
    conn.close()

def get_whitelist_ids():
    conn = sqlite3.connect("whitelist.db")
    c = conn.cursor()

    c.execute("SELECT id FROM ids")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def memory_add(chat_id: int, facts: list):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    for fact in facts:
        c.execute("INSERT OR IGNORE INTO memory (chat_id, content) VALUES (?, ?)", (chat_id, fact))
    conn.commit()
    conn.close()

def memory_remove(chat_id: int, facts: list):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    for fact in facts:
        c.execute("DELETE FROM memory WHERE chat_id = ? AND content = ?", (chat_id, fact))
    conn.commit()
    conn.close()

def memory_get(chat_id: int, n: int):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT content FROM memory WHERE chat_id = ? ORDER BY id LIMIT 1 OFFSET ?", (chat_id, n))
    mem = c.fetchone()
    fact = mem[0] if mem else None
    conn.close()
    return fact

def memory_get_all(chat_id: int):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT content FROM memory WHERE chat_id = ? ORDER BY id", (chat_id,))
    memory = ""
    for n, fact in enumerate(c.fetchall()):
        memory += f"{n}. {fact[0]}\n\n"
    conn.close()
    return memory if memory else "Пусто!"
