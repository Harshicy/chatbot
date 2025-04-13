from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import nltk
import os
import sqlite3
from datetime import datetime
import json
import random
import logging
from cryptography.fernet import Fernet

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Generate a key for Fernet (store securely in production)
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Set up NLTK
nltk_data_path = os.path.join(os.getcwd(), 'nltk_data')
if not os.path.exists(nltk_data_path):
    os.makedirs(nltk_data_path)
nltk.data.path.append(nltk_data_path)
try:
    nltk.download('punkt', download_dir=nltk_data_path, quiet=True)
    nltk.download('wordnet', download_dir=nltk_data_path, quiet=True)
except Exception as e:
    logger.error(f"NLTK download failed: {e}")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Knowledge base
knowledge_base = {
    "greetings": ["Hello! How can I assist you today?", "Hi there! What’s on your mind?", "Hey! Ready to chat?",
                  "Good day! How may I help you?", "Greetings! What can I do for you?", "Yo! What’s up?"],
    "farewells": ["Goodbye! Come back soon!", "See you later!", "Take care!", "Farewell! Visit again!",
                  "Catch you later!", "Have a great day!"],
    "how_are_you": ["I'm doing great, thanks for asking! How about you?", "As an AI, I'm always good! How can I help you today?",
                    "Feeling fantastic! What about you?", "I'm awesome, thanks! How are you feeling?",
                    "Doing well! How can I make your day better?"],
    "name": ["I'm Harsha's Chatbot, created to assist you!", "You can call me Harsha's Chatbot!",
             "I’m your friendly Harsha's Chatbot!", "Meet Harsha's Chatbot, at your service!"],
    "weather": ["I can’t check the weather, but I’d love to talk about something else! What’s on your mind?",
                "Weather’s not my thing, but let’s chat about something fun! Any ideas?",
                "No weather updates here, but I’m happy to discuss anything else!"],
    "help": ["I can chat with you! Try asking about my name, how I am, or anything you like!",
             "I’m here to help! Ask me anything—my name, how I’m doing, or more!",
             "Need assistance? Try questions about me or anything you’re curious about!"],
    "time": ["I don’t have a clock, but I’d love to chat about your day! What time is it for you?",
             "Time’s a mystery to me, but tell me about your schedule!",
             "No time here, but let’s talk about what’s on your mind!"],
    "hobbies": ["I don’t have hobbies, but I love chatting! What do you enjoy?",
                "Hobbies? I’d say talking to you is mine! What about you?",
                "I’m all about conversation! What hobbies do you have?"],
    "food": ["I don’t eat, but I’d love to hear about your favorite food!",
             "Food sounds delicious! What’s your go-to dish?",
             "No taste buds here, but tell me about your favorite meal!"],
    "travel": ["Travel sounds exciting! Where have you been?",
               "I’d love to explore through your stories! Where have you traveled?",
               "No vacations for me, but tell me about your travel adventures!"],
    "default": ["That’s interesting! Can you tell me more?", "I’m not sure I understand, could you elaborate?",
                "Let’s explore that—tell me more!", "Hmm, fascinating! What else can you share?",
                "I’m intrigued! Please go on.", "Tell me more—I’m all ears!"]
}

def get_response(message):
    if not message or not isinstance(message, str):
        logger.warning("Invalid message input")
        return "Please provide a valid message!"
    message = message.lower().strip()
    for category, responses in knowledge_base.items():
        if any(keyword in message for keyword in category.split('_')) or any(word in message for word in category.split()):
            logger.debug(f"Matched category: {category}")
            return random.choice(responses)
    logger.debug("No category matched, using default")
    return random.choice(knowledge_base["default"])

def init_db():
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, name TEXT, email TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chats
                 (id INTEGER PRIMARY KEY, user_id TEXT, chat_id TEXT, message TEXT, is_user INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_user(username):
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user

def encrypt_credentials(username, password, name=None, email=None):
    credentials = {"username": username, "password": password, "name": name, "email": email}
    credentials_json = json.dumps(credentials).encode()
    encrypted_data = cipher_suite.encrypt(credentials_json)
    with open('credentials.enc', 'wb') as f:
        f.write(encrypted_data)

def decrypt_credentials():
    credentials_file = 'credentials.enc'
    if not os.path.exists(credentials_file):
        return {}
    try:
        with open(credentials_file, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = cipher_suite.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return {}

def save_message(user_id, message, is_user, chat_id=None):
    if chat_id is None:
        chat_id = f"chat_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO chats (user_id, chat_id, message, is_user, timestamp) VALUES (?, ?, ?, ?, ?)",
              (user_id, chat_id, message, is_user, timestamp))
    conn.commit()
    conn.close()
    return chat_id

def get_chat_history(user_id, chat_id):
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT timestamp, message, is_user FROM chats WHERE user_id = ? AND chat_id = ? ORDER BY timestamp ASC",
              (user_id, chat_id))
    history = [{"timestamp": row[0], "message": row[1], "isUser": bool(row[2])} for row in c.fetchall()]
    conn.close()
    return history

@app.route("/")
def home():
    if not session.get('logged_in'):
        credentials = decrypt_credentials()
        if credentials and 'username' in credentials and 'password' in credentials:
            username = credentials['username']
            user = get_user(username)
            if user and check_password_hash(user[2], credentials['password']):
                session['logged_in'] = True
                session['user_id'] = username
                session['current_chat_id'] = f"chat_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                return redirect(url_for('home'))
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    current_chat_id = session.get('current_chat_id')
    return render_template("index.html", logged_in=True, user_id=user_id, username=user_id, current_chat_id=current_chat_id)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = get_user(username)
        if user and check_password_hash(user[2], password):
            session['logged_in'] = True
            session['user_id'] = username
            session['current_chat_id'] = f"chat_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            encrypt_credentials(username, password, user[3], user[4])  # Include name and email
            return redirect(url_for('home'))
        return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('current_chat_id', None)
    return redirect(url_for('login'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        name = request.form.get("name")
        email = request.form.get("email")
        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters")
        if get_user(username):
            return render_template("register.html", error="Username already exists")
        hashed_password = generate_password_hash(password)
        conn = sqlite3.connect('chat_history.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)",
                  (username, hashed_password, name, email))
        conn.commit()
        conn.close()
        encrypt_credentials(username, password, name, email)
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/get_response", methods=["POST"])
def get_response_route():
    if not session.get('logged_in'):
        return "Please log in to chat"
    try:
        user_message = request.form.get("message")
        user_id = session.get('user_id')
        current_chat_id = session.get('current_chat_id', f"chat_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        logger.debug(f"Received message: {user_message}, Chat ID: {current_chat_id}")
        if user_message:
            response = get_response(user_message)
            logger.debug(f"Generated response: {response}")
            save_message(user_id, user_message, True, current_chat_id)
            save_message(user_id, response, False, current_chat_id)
            session['current_chat_id'] = current_chat_id  # Ensure chat ID is persisted
            return response
        return "No message provided"
    except Exception as e:
        logger.error(f"Error in get_response: {e}")
        return "An error occurred. Please try again."

@app.route("/save_message", methods=["POST"])
def save_message():
    if not session.get('logged_in'):
        return "Unauthorized"
    try:
        user_id = session.get('user_id')
        message = request.form.get("message")
        is_user = request.form.get("isUser") == "true"
        chat_id = request.form.get("chatId") or session.get('current_chat_id')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect('chat_history.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO chats (user_id, chat_id, message, is_user, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (user_id, chat_id, message, is_user, timestamp))
        conn.commit()
        conn.close()
        return jsonify({"status": "OK", "chatId": chat_id})
    except Exception as e:
        logger.error(f"Error in save_message: {e}")
        return jsonify({"status": "Error", "message": str(e)})

@app.route("/get_history")
def get_history():
    if not session.get('logged_in'):
        return jsonify({"error": "Please log in"})
    try:
        user_id = session.get('user_id')
        chat_id = request.args.get('chatId') or session.get('current_chat_id')
        history = get_chat_history(user_id, chat_id)
        conn = sqlite3.connect('chat_history.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT DISTINCT chat_id FROM chats WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        chat_ids = [row[0] for row in c.fetchall()]
        conn.close()
        return jsonify({"history": history, "chatIds": chat_ids})
    except Exception as e:
        logger.error(f"Error in get_history: {e}")
        return jsonify({"error": "Failed to load history"})

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    user = get_user(user_id)
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        new_password = request.form.get("new_password")
        if new_password and len(new_password) >= 6:
            hashed_password = generate_password_hash(new_password)
            conn = sqlite3.connect('chat_history.db', check_same_thread=False)
            c = conn.cursor()
            c.execute("UPDATE users SET password = ?, name = ?, email = ? WHERE username = ?",
                      (hashed_password, name or user[3], email or user[4], user_id))
            conn.commit()
            conn.close()
            encrypt_credentials(user_id, new_password, name, email)
        return redirect(url_for('home'))
    return render_template("settings.html", user=user)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)