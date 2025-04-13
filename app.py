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
import re

# Set up logging
logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='w')
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

# Load or initialize knowledge base
KNOWLEDGE_BASE_FILE = 'knowledge_base.json'
if os.path.exists(KNOWLEDGE_BASE_FILE):
    with open(KNOWLEDGE_BASE_FILE, 'r') as f:
        knowledge_base = json.load(f)
else:
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
        "weather": ["I can’t check the weather directly, but I can search for the latest updates! Please tell me a location.",
                    "Weather info? Let me look it up for you! Where are you interested in?",
                    "I’ll fetch the latest weather data. Please provide a city or place!"],
        "great_wall_of_china": ["The Great Wall of China is an ancient fortification built to protect against invasions, stretching over 21,000 km. Want more details?",
                               "It’s a UNESCO World Heritage site, constructed over centuries, with the Ming Dynasty section being the most famous. Ask me more!",
                               "A symbol of Chinese history, the wall dates back over 2,000 years. Interested in its length or weather?"],
        "history": ["History is vast! Tell me a topic (e.g., Great Wall, wars), and I’ll share what I know.",
                    "I can talk about ancient civilizations, wars, or dynasties. What interests you?",
                    "From Egypt to China, history is full of stories. Pick a subject!"],
        "travel": ["Love to travel? Tell me a destination, and I’ll give you tips or info!",
                   "Traveling is fun! Where are you headed? I can suggest the best times to visit.",
                   "I can help with travel plans. Name a place, and I’ll assist!"],
        "general": ["That’s interesting! Can you tell me more?", "I’m learning as we go. Elaborate, please!",
                    "Fascinating! Share more details so I can assist better."]
    }
    with open(KNOWLEDGE_BASE_FILE, 'w') as f:
        json.dump(knowledge_base, f)

def web_search(query):
    # Simulate real-time search using preloaded web results (replace with actual API in production)
    logger.debug(f"Searching web for: {query}")
    results = {
        "weather": "Check weather.com.cn for real-time updates. As of April 12, 2025, Beijing is around 15°C with clear skies.",
        "great wall of china": "The Great Wall of China, over 21,000 km long, was built to defend against invasions, with the Ming Dynasty section (8,850 km) being iconic. Best visited in spring or autumn."
    }.get(query.lower(), f"No real-time data available for {query}. Let me learn from you!")
    return results

def get_response(message):
    logger.debug(f"get_response called with message: {message}")
    if not message or not isinstance(message, str):
        logger.warning("Invalid message input")
        return "Please provide a valid message!"
    try:
        message = message.lower().strip()
        # Check for dynamic queries
        if "weather" in message and "where" in message:
            location = re.search(r"where (.*)\?", message)
            if location:
                return web_search("weather") + f" For {location.group(1)}, check a local forecast site!"
            return web_search("weather")
        elif "great wall of china" in message:
            return web_search("great wall of china")
        elif any(cat in message for cat in knowledge_base.keys()):
            for category, responses in knowledge_base.items():
                if category in message:
                    return random.choice(responses)
        # Adaptive learning: Add new knowledge
        if "?" in message and not any(cat in message for cat in knowledge_base.keys()):
            user_response = input("Please provide an answer to add to my knowledge: ")  # Simulate user input (replace with UI in production)
            if user_response and len(user_response.split()) > 3:  # Basic validation
                new_category = re.sub(r'\W+', '_', message.split('?')[0].strip())
                if new_category not in knowledge_base:
                    knowledge_base[new_category] = []
                knowledge_base[new_category].append(user_response)
                with open(KNOWLEDGE_BASE_FILE, 'w') as f:
                    json.dump(knowledge_base, f)
                return f"Thanks! I’ve learned: {user_response}"
        return random.choice(knowledge_base["general"])
    except Exception as e:
        logger.error(f"Error in get_response logic: {e}")
        return "Error processing your request."

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
        chat_id = f"chat_{user_id}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute("INSERT INTO chats (user_id, chat_id, message, is_user, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (user_id, chat_id, message, is_user, timestamp))
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error in save_message: {e}")
    finally:
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
                session['current_chat_id'] = f"chat_{username}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
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
            session['current_chat_id'] = f"chat_{username}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
            encrypt_credentials(username, password, user[3], user[4])
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
    logger.debug("get_response route hit")
    if not session.get('logged_in'):
        logger.warning("User not logged in")
        return "Please log in to chat"
    try:
        user_message = request.form.get("message")
        user_id = session.get('user_id')
        current_chat_id = session.get('current_chat_id', f"chat_{user_id}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}")
        logger.debug(f"Processing message: {user_message}, User ID: {user_id}, Chat ID: {current_chat_id}")
        if not user_message:
            logger.warning("No message provided")
            return "No message provided"
        response = get_response(user_message)
        logger.debug(f"Response generated: {response}")
        save_message(user_id, user_message, True, current_chat_id)
        save_message(user_id, response, False, current_chat_id)
        session['current_chat_id'] = current_chat_id
        return response
    except Exception as e:
        logger.error(f"Exception in get_response_route: {str(e)} with traceback: {str(e.__traceback__)}")
        return "An error occurred. Please try again."

@app.route("/save_message", methods=["POST"])
def save_message_route():
    if not session.get('logged_in'):
        return jsonify({"status": "Unauthorized"})
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
        logger.error(f"Error in save_message: {str(e)}")
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
        logger.error(f"Error in get_history: {str(e)}")
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