import sqlite3

# Connect to your SQLite database
conn = sqlite3.connect("history.db")
c = conn.cursor()

# Try adding the email column WITHOUT UNIQUE
try:
    c.execute("ALTER TABLE users ADD COLUMN email TEXT")
    print("✅ 'email' column added successfully.")
except sqlite3.OperationalError as e:
    print("⚠️ Column might already exist or failed:", e)

# Commit and close
conn.commit()
conn.close()
