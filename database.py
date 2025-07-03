import sqlite3
from datetime import datetime

DB_NAME = "history.db"

# Initialize the database
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            style TEXT NOT NULL,
            filename TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def insert_history(prompt, style, filename):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO history (prompt, style, filename, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (prompt, style, filename, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_all_history(limit=10):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT prompt, style, filename, timestamp
        FROM history
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(zip(["prompt", "style", "filename", "timestamp"], row)) for row in rows]

def delete_history_by_filename(filename):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM history WHERE filename = ?', (filename,))
    conn.commit()
    conn.close()
