from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import nltk
import os
import sqlite3
from nltk.chat.util import Chat, reflections
from datetime import datetime

# Set up NLTK
nltk_data_path = os.path.join(os.getcwd(), 'nltk_data')
if not os.path.exists(nltk_data_path):
    os.makedirs(nltk_data_path)
nltk.data.path.append(nltk_data_path)
try:
    nltk.download('punkt', download_dir=nltk_data_path, quiet=True)
except Exception as e:
    print(f"NLTK download failed: {e}")

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management; in production, use a secure key

# Initialize chatbot
pairs = [
    [r"hi|hello|hey", ["Hello!", "Hi there!", "Hey! How can I help you?"]],
    [r"how are you", ["I'm doing great, thanks! How about you?", "As an AI, I'm always good!"]],
    [r"what is your name", ["I'm Grok, nice to meet you!", "My name is Grok, created by xAI"]],
    [r"bye|goodbye", ["See you later!", "Goodbye!", "Have a great day!"]],
    [r"what can you do", ["I can chat with you! Try asking my name or how I am."]],
    [r"(.*) weather (.*)", ["I'm not a weather bot, but I can chat about other things!"]],
    [r"(.*)", ["Interesting! Tell me more.", "Can you clarify that?", "I'm listening..."]]
]
chatbot = Chat(pairs, reflections)

# SQLite database setup
def init_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, user_id TEXT, message TEXT, is_user INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_user(username):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user

@app.route("/")
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    return render_template("index.html", logged_in=True, user_id=user_id)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = get_user(username)
        if user and check_password_hash(user[2], password):
            session['logged_in'] = True
            session['user_id'] = username  # Use username as user_id
            return redirect(url_for('home'))
        return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if get_user(username):
            return render_template("register.html", error="Username already exists")
        hashed_password = generate_password_hash(password)
        conn = sqlite3.connect('chat_history.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/get_response", methods=["POST"])
def get_response():
    if not session.get('logged_in'):
        return "Please log in to chat"
    user_message = request.form.get("message")
    user_id = session.get('user_id')
    if user_message:
        response = chatbot.respond(user_message)
        save_message(user_id, user_message, True)
        save_message(user_id, response, False)
        return response
    return "No message provided"

@app.route("/save_message", methods=["POST"])
def save_message():
    if not session.get('logged_in'):
        return "Unauthorized"
    user_id = session.get('user_id')
    message = request.form.get("message")
    is_user = request.form.get("isUser") == "true"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (user_id, message, is_user, timestamp) VALUES (?, ?, ?, ?)",
              (user_id, message, is_user, timestamp))
    conn.commit()
    conn.close()
    return "OK"

@app.route("/get_history")
def get_history():
    if not session.get('logged_in'):
        return jsonify({"error": "Please log in"})
    user_id = session.get('user_id')
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT timestamp, message, is_user FROM messages WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    history = [{"timestamp": row[0], "message": row[1], "isUser": bool(row[2])} for row in c.fetchall()]
    conn.close()
    return jsonify(history)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)