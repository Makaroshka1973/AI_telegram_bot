import sqlite3
from datetime import datetime

def init_db():
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

    # indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_chat_id ON messages (chat_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON messages (timestamp)')

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
