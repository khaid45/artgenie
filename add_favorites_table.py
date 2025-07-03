import sqlite3

try:
    conn = sqlite3.connect("history.db")
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            UNIQUE(user_id, filename)
        )
    ''')

    conn.commit()
    print("✅ 'favorites' table added successfully.")

except Exception as e:
    print("❌ Error creating table:", str(e))

finally:
    conn.close()
