from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
import sqlite3
from datetime import datetime
from models.model_loader import load_model
from werkzeug.security import generate_password_hash, check_password_hash
import zipfile
from io import BytesIO
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your-secret-key"

# Load the model once
pipe = load_model()

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
DB_FILE = os.path.join(BASE_DIR, "history.db")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Style options
STYLE_SUFFIXES = {
    "realistic": "",
    "cartoon": "in cartoon style",
    "anime": "in anime style",
    "painting": "in oil painting style",
    "artistic": "in artistic illustration style",
    "sketch": "as a pencil sketch"
}

# --- SQLite DB Setup ---
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# Create history table
c.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        prompt TEXT,
        style TEXT,
        filename TEXT,
        timestamp TEXT
    )
''')

# Create user table with email
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
''')

# Create favorites table
c.execute('''
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        filename TEXT,
        UNIQUE(user_id, filename)
    )
''')

conn.commit()

# --- Flask-Login User Loader ---
class User(UserMixin):
    def __init__(self, id_, username, email, password):
        self.id = id_
        self.username = username
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    c.execute("SELECT id, username, email, password FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    if row:
        return User(*row)
    return None

# --- ROUTES ---

@app.route("/")
@login_required
def index():
    return render_template("index.html", username=current_user.username)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        c.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if c.fetchone():
            flash("Username or email already exists")
            return redirect(url_for("signup"))

        hashed_pw = generate_password_hash(password)
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_pw))
        conn.commit()
        flash("Account created. Please log in.")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        c.execute("SELECT id, username, email, password FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        if row and check_password_hash(row[3], password):
            user = User(*row)
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid username or password")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/generate", methods=["POST"])
@login_required
def generate():
    try:
        prompt = request.form.get("prompt", "").strip()
        style = request.form.get("style", "realistic")
        styled_prompt = f"{prompt}, {STYLE_SUFFIXES.get(style, '')}".strip().strip(',')

        print(f"[INFO] Generating image with prompt: '{styled_prompt}'")

        image = pipe(styled_prompt, num_inference_steps=25).images[0]
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        image.save(filepath)

        entry = {
            "user_id": current_user.id,
            "prompt": prompt,
            "style": style,
            "filename": filename,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_history(entry)
        print(f"[SUCCESS] Image saved: {filename}")
        return jsonify(entry)

    except Exception as e:
        print(f"[ERROR] Failed to generate image: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/outputs/<filename>")
def get_image(filename):
    safe_name = secure_filename(filename)
    filepath = os.path.join(OUTPUT_DIR, safe_name)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype="image/png")
    else:
        return "File not found", 404

@app.route("/history")
@login_required
def get_history():
    c.execute("SELECT prompt, style, filename, timestamp FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 10", (current_user.id,))
    rows = c.fetchall()
    history = [
        {
            "prompt": row[0],
            "style": row[1],
            "filename": row[2],
            "timestamp": row[3]
        }
        for row in rows
    ]
    return jsonify(history)

@app.route("/favorites")
@login_required
def get_favorites():
    c.execute("SELECT filename FROM favorites WHERE user_id = ?", (current_user.id,))
    files = [row[0] for row in c.fetchall()]
    return jsonify(files)

@app.route("/favorite", methods=["POST"])
@login_required
def favorite_image():
    data = request.get_json()
    filename = data.get("filename")
    try:
        c.execute("INSERT OR IGNORE INTO favorites (user_id, filename) VALUES (?, ?)", (current_user.id, filename))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/unfavorite", methods=["POST"])
@login_required
def unfavorite_image():
    data = request.get_json()
    filename = data.get("filename")
    c.execute("DELETE FROM favorites WHERE user_id = ? AND filename = ?", (current_user.id, filename))
    conn.commit()
    return jsonify({"status": "success"})

@app.route("/delete", methods=["POST"])
@login_required
def delete_image():
    data = request.get_json()
    filename = data.get("filename")
    filepath = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"[DELETE] Removed file: {filename}")

    c.execute("DELETE FROM history WHERE filename = ? AND user_id = ?", (filename, current_user.id))
    c.execute("DELETE FROM favorites WHERE filename = ? AND user_id = ?", (filename, current_user.id))
    conn.commit()

    return jsonify({"status": "success", "deleted": filename})

@app.route("/export-history")
@login_required
def export_history():
    import csv
    from io import StringIO

    si = StringIO()
    writer = csv.writer(si)

    writer.writerow(["Prompt", "Style", "Filename", "Timestamp"])
    c.execute("SELECT prompt, style, filename, timestamp FROM history WHERE user_id = ?", (current_user.id,))
    rows = c.fetchall()
    writer.writerows(rows)

    return app.response_class(
        response=si.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=artgenie_history.csv"}
    )

@app.route("/download-zip")
@login_required
def download_zip():
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        c.execute("SELECT filename FROM history WHERE user_id = ?", (current_user.id,))
        rows = c.fetchall()
        for row in rows:
            filepath = os.path.join(OUTPUT_DIR, row[0])
            if os.path.exists(filepath):
                zipf.write(filepath, arcname=row[0])

    zip_buffer.seek(0)
    return Response(
        zip_buffer.getvalue(),
        mimetype='application/zip',
        headers={"Content-Disposition": "attachment; filename=artgenie_images.zip"}
    )

@app.route("/profile")
@login_required
def profile():
    c.execute("SELECT COUNT(*), MAX(timestamp) FROM history WHERE user_id = ?", (current_user.id,))
    total_images, last_time = c.fetchone()

    c.execute("SELECT COUNT(*) FROM favorites WHERE user_id = ?", (current_user.id,))
    total_favorites = c.fetchone()[0]

    c.execute("SELECT style, COUNT(style) as count FROM history WHERE user_id = ? GROUP BY style ORDER BY count DESC LIMIT 1", (current_user.id,))
    row = c.fetchone()
    most_used_style = row[0] if row else "N/A"

    c.execute("SELECT prompt FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 1", (current_user.id,))
    row = c.fetchone()
    last_prompt = row[0] if row else "N/A"

    return render_template("profile.html", username=current_user.username,
                           total_images=total_images or 0,
                           total_favorites=total_favorites or 0,
                           most_used_style=most_used_style,
                           last_time=last_time or "N/A",
                           last_prompt=last_prompt)

def save_history(entry):
    c.execute(
        "INSERT INTO history (user_id, prompt, style, filename, timestamp) VALUES (?, ?, ?, ?, ?)",
        (entry["user_id"], entry["prompt"], entry["style"], entry["filename"], entry["timestamp"])
    )
    conn.commit()
    # ... (rest of your existing code remains unchanged)

@app.route("/style-distribution")
@login_required
def style_distribution():
    c.execute("SELECT style, COUNT(*) FROM history WHERE user_id = ? GROUP BY style", (current_user.id,))
    rows = c.fetchall()
    return jsonify({style: count for style, count in rows})

if __name__ == "__main__":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.run(host="0.0.0.0", port=5000)

