from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename, safe_join
import nltk
import os
import sqlite3
from datetime import datetime
import json
import re
import logging
from cryptography.fernet import Fernet
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv

# Initialize logging with detailed output
logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='w')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env', override=True)
API_KEY = os.getenv("WEATHER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
ZAPIER_WEBHOOK_URL = os.getenv("ZAPIER_WEBHOOK_URL")

logger.debug(f"API_KEY: {API_KEY is not None}, OPENAI_API_KEY: {OPENAI_API_KEY is not None}, "
             f"NEWSAPI_KEY: {NEWSAPI_KEY is not None}, ZAPIER_WEBHOOK_URL: {ZAPIER_WEBHOOK_URL is not None}")
if not API_KEY:
    logger.error("WEATHER_API_KEY is not set.")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is not set. OpenAI features may not work.")
if not NEWSAPI_KEY:
    logger.error("NEWSAPI_KEY is not set.")
if not ZAPIER_WEBHOOK_URL:
    logger.error("ZAPIER_WEBHOOK_URL is not set.")

# Set up NLTK
nltk_data_path = os.path.join(os.getcwd(), 'nltk_data')
if not os.path.exists(nltk_data_path):
    os.makedirs(nltk_data_path)
nltk.data.path.append(nltk_data_path)
try:
    nltk.download('punkt', download_dir=nltk_data_path, quiet=True)
    nltk.download('wordnet', download_dir=nltk_data_path, quiet=True)
    nltk.download('averaged_perceptron_tagger', download_dir=nltk_data_path, quiet=True)
except Exception as e:
    logger.error(f"NLTK download failed: {e}")

# Optional OpenAI import
try:
    import openai
    openai.api_key = OPENAI_API_KEY
    openai_available = bool(openai and OPENAI_API_KEY)
except ImportError:
    openai = None
    openai_available = False
    logger.warning("OpenAI module not found. AI features will use fallback responses.")

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = os.urandom(24)
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Knowledge base
KNOWLEDGE_BASE_FILE = 'knowledge_base.json'
if os.path.exists(KNOWLEDGE_BASE_FILE):
    with open(KNOWLEDGE_BASE_FILE, 'r') as f:
        knowledge_base = json.load(f)
else:
    knowledge_base = {}
    with open(KNOWLEDGE_BASE_FILE, 'w') as f:
        json.dump(knowledge_base, f)

def web_search(query):
    try:
        if not API_KEY:
            return "API key not configured. Please contact the administrator."
        if "weather" in query.lower():
            location = re.search(r"where (.*)\?", query) or re.search(r"in (.*)", query)
            if location:
                city = location.group(1).strip()
                url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={city}&aqi=no"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return f"Current weather in {city}: {data['current']['temp_c']}°C, {data['current']['condition']['text']}."
                logger.error(f"Weather API failed for {city}: {response.status_code}")
                return f"Could not fetch weather for {city}. Try again later."
            return "Please specify a city (e.g., 'weather in London')."
        elif "great wall of china" in query.lower():
            url = "https://en.wikipedia.org/wiki/Great_Wall_of_China"
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraph = soup.find('p')
            return paragraph.text[:200] + "..." if paragraph else "The Great Wall of China is a historic fortification built to protect against invasions, stretching over 21,000 km."
        else:
            return f"Searching for {query}. [Simulated result - integrate a real API]."
    except requests.RequestException as e:
        logger.error(f"Web search error: {e}")
        return f"Error fetching data for {query}. Check your connection."
    except Exception as e:
        logger.error(f"Unexpected error in web_search: {e}")
        return "Error processing your request. Try again."

def process_query(message):
    logger.debug(f"Processing query: {message}")
    if not message or not isinstance(message, str):
        return "Please provide a valid question!"

    try:
        message = message.lower().strip()
        tokens = nltk.word_tokenize(message)
        tagged = nltk.pos_tag(tokens)

        if "weather" in message:
            return web_search(message)
        elif "great wall of china" in message:
            return web_search(message)
        elif "time" in message:
            return f"The current time is {datetime.now().strftime('%H:%M:%S')} on {datetime.now().strftime('%Y-%m-%d')}."
        elif "?" in message:
            for category, responses in knowledge_base.items():
                if category in message:
                    return responses[0] if responses else "I’m learning about this. Provide more info!"
            if not any(cat in message for cat in knowledge_base.keys()):
                return "I don’t know yet. Tell me the answer, and I’ll learn it!"

        if "news" in message:
            topic = message.split("news")[1].strip() if "news" in message else "general"
            if not NEWSAPI_KEY:
                return "NewsAPI key not configured."
            url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={NEWSAPI_KEY}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok" and data.get("articles"):
                    article = data["articles"][0]
                    return f"Headline: {article['title']}\nSource: {article['source']['name']}\nURL: {article['url']}"
                logger.error(f"NewsAPI failed for {topic}: {response.status_code}")
                return "Couldn’t fetch news."
            return "Error fetching news. Check your connection."

        if "schedule" in message or "task" in message:
            if not ZAPIER_WEBHOOK_URL:
                return "Zapier webhook URL not configured."
            task = message.replace("schedule", "").replace("task", "").strip() or "New task from chatbot"
            payload = {"task": task, "date": "tomorrow"}
            response = requests.post(ZAPIER_WEBHOOK_URL, json=payload, timeout=5)
            if response.status_code == 200:
                return f"Task '{task}' scheduled via Zapier!"
            logger.error(f"Zapier API failed: {response.status_code}")
            return "Failed to schedule task."

        if any(word in message for word in ["hi", "hello", "hey"]):
            return "Hello! How can I assist you today?"
        elif any(word in message for word in ["who are you", "what are you"]):
            return "I’m a chatbot, built by harsha, designed to provide helpful answers."
        elif any(word in ["help", "assist"] for word, pos in tagged if pos.startswith('VB')):
            return "I can assist with weather, time, news, scheduling, or learn new things. Ask me anything!"
        elif any(word in ["bye", "goodbye"] for word in tokens):
            return "Goodbye! Return anytime."
        elif any(pos in ['NN', 'NNS'] for _, pos in tagged):
            return f"I see you mentioned {tokens[0]}. Provide more context or ask a question."
        else:
            if openai and OPENAI_API_KEY:
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": message}],
                        max_tokens=150,
                        temperature=0.7
                    )
                    return response.choices[0].message.content.strip()
                except openai.error.OpenAIError as e:
                    logger.error(f"OpenAI API error: {e}")
                    return "OpenAI API error. Using fallback response."
                except Exception as e:
                    logger.error(f"Unexpected OpenAI error: {e}")
                    return "OpenAI error. Using fallback response."
            return "I’m not sure how to respond. Try 'hi', 'weather in [city]', 'news about tech', or teach me something."

    except Exception as e:
        logger.error(f"Error in process_query: {e}")
        return "Error processing your request. Try again."

def save_learned_knowledge(question, answer):
    category = re.sub(r'\W+', '_', question.split('?')[0].strip())
    if category not in knowledge_base:
        knowledge_base[category] = []
    knowledge_base[category].append(answer)
    with open(KNOWLEDGE_BASE_FILE, 'w') as f:
        json.dump(knowledge_base, f)
    return "Thank you! I’ve learned: " + answer

def init_db():
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    # Create the users table with initial columns
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, name TEXT, email TEXT)''')
    # Add new columns if they don't exist (migration logic)
    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]
    if 'two_factor_enabled' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN two_factor_enabled INTEGER DEFAULT 0")
    if 'email_notifications' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN email_notifications INTEGER DEFAULT 1")
    if 'sms_notifications' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN sms_notifications INTEGER DEFAULT 0")
    if 'security_question1' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN security_question1 TEXT")
    if 'security_answer1' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN security_answer1 TEXT")
    if 'security_question2' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN security_question2 TEXT")
    if 'security_answer2' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN security_answer2 TEXT")
    if 'profile_picture' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN profile_picture TEXT")
    # Create the chats table
    c.execute('''CREATE TABLE IF NOT EXISTS chats
                 (id INTEGER PRIMARY KEY, user_id TEXT, chat_id TEXT, message TEXT, is_user INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_user(username):
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        columns = ['id', 'username', 'password', 'name', 'email', 'two_factor_enabled', 'email_notifications',
                   'sms_notifications', 'security_question1', 'security_answer1', 'security_question2',
                   'security_answer2', 'profile_picture']
        return dict(zip(columns, row))
    return None

def encrypt_credentials(username, password, name=None, email=None, two_factor_enabled=None, email_notifications=None, 
                       sms_notifications=None, security_question1=None, security_answer1=None, 
                       security_question2=None, security_answer2=None, profile_picture=None):
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)
    credentials = {
        "username": username, "password": password, "name": name, "email": email,
        "two_factor_enabled": two_factor_enabled, "email_notifications": email_notifications,
        "sms_notifications": sms_notifications, "security_question1": security_question1,
        "security_answer1": security_answer1, "security_question2": security_question2,
        "security_answer2": security_answer2, "profile_picture": profile_picture
    }
    encrypted_data = cipher_suite.encrypt(json.dumps(credentials).encode())
    with open('credentials.enc', 'wb') as f:
        f.write(encrypted_data)
    with open('key.key', 'wb') as f:
        f.write(key)

def decrypt_credentials():
    if not os.path.exists('credentials.enc') or not os.path.exists('key.key'):
        return {}
    try:
        with open('key.key', 'rb') as f:
            key = f.read()
        with open('credentials.enc', 'rb') as f:
            encrypted_data = f.read()
        return json.loads(Fernet(key).decrypt(encrypted_data).decode())
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

def delete_chat(user_id, chat_id):
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM chats WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        conn.commit()
        return {"status": "OK", "message": f"Chat {chat_id} deleted"}
    except sqlite3.Error as e:
        logger.error(f"Database error in delete_chat: {e}")
        return {"status": "Error", "message": str(e)}
    finally:
        conn.close()

@app.route("/")
def home():
    logger.debug("Accessing home route")
    # Disable auto-login on initial access, only allow after manual login
    if not session.get('logged_in'):
        session.clear()  # Clear any existing session
        logger.debug("No active session, redirecting to login")
        return redirect(url_for('login'))
    # Proceed only if logged in via /login
    user_id = session.get('user_id')
    current_chat_id = request.args.get('chatId') or session.get('current_chat_id')
    if not current_chat_id:
        current_chat_id = f"chat_{user_id}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
        session['current_chat_id'] = current_chat_id
    history = get_chat_history(user_id, current_chat_id)
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT DISTINCT chat_id FROM chats WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    chat_ids = [row[0] for row in c.fetchall()]
    conn.close()
    logger.debug(f"Rendering index.html for user: {user_id}, current_chat_id: {current_chat_id}")
    return render_template("index.html", logged_in=True, user_id=user_id, current_chat_id=current_chat_id, history=history, chatIds=chat_ids, openai_available=openai_available)

@app.route("/login", methods=["GET", "POST"])
def login():
    logger.debug(f"Accessing login route, method: {request.method}")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        logger.debug(f"Login attempt for username: {username}")
        user = get_user(username)
        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['user_id'] = username
            session['current_chat_id'] = f"chat_{username}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
            encrypt_credentials(username, password, user['name'], user['email'], user['two_factor_enabled'], user['email_notifications'], user['sms_notifications'], user['security_question1'], user['security_answer1'], user['security_question2'], user['security_answer2'], user['profile_picture'])
            logger.debug(f"Successful login for user: {username}")
            return redirect(url_for('home'))
        logger.debug("Login failed: Invalid username or password")
        return render_template("login.html", error="Invalid username or password")
    logger.debug("Rendering login page")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    logger.debug("Accessing logout route")
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('current_chat_id', None)
    logger.debug("User logged out, redirecting to login")
    return redirect(url_for('login'))

@app.route("/register", methods=["GET", "POST"])
def register():
    logger.debug(f"Accessing register route, method: {request.method}")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        name = request.form.get("name")
        email = request.form.get("email")
        logger.debug(f"Registration attempt for username: {username}")
        if len(password) < 6:
            logger.debug("Registration failed: Password too short")
            return render_template("register.html", error="Password must be at least 6 characters")
        if get_user(username):
            logger.debug("Registration failed: Username already exists")
            return render_template("register.html", error="Username already exists")
        hashed_password = generate_password_hash(password)
        conn = sqlite3.connect('chat_history.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, name, email) VALUES (?, ?, ?, ?)",
                  (username, hashed_password, name, email))
        conn.commit()
        conn.close()
        encrypt_credentials(username, password, name, email)
        logger.debug(f"Successful registration for user: {username}")
        return redirect(url_for('login'))
    logger.debug("Rendering register page")
    return render_template("register.html")

@app.route("/get_response_route", methods=["POST"])
def get_response_route():
    logger.debug("Accessing get_response route")
    if not session.get('logged_in'):
        logger.debug("Unauthorized access to get_response")
        return "Please log in to chat"
    try:
        user_message = request.form.get("message")
        user_id = session.get('user_id')
        chat_id = request.form.get("chatId") or session.get('current_chat_id', f"chat_{user_id}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}")
        logger.debug(f"Processing message: {user_message} for user: {user_id}, chat_id: {chat_id}")
        if not user_message:
            logger.debug("No message provided")
            return "No message provided"
        if "new chat" in user_message.lower():
            chat_id = f"chat_{user_id}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
            session['current_chat_id'] = chat_id
            logger.debug(f"New chat started, chat_id: {chat_id}")
            save_message(user_id, "New chat started!", False, chat_id)
            return "New chat started!"
        response = process_query(user_message)
        save_message(user_id, user_message, True, chat_id)
        save_message(user_id, response, False, chat_id)
        session['current_chat_id'] = chat_id
        logger.debug(f"Response sent: {response}")
        return response
    except Exception as e:
        logger.error(f"Exception in get_response_route: {e}")
        return "An error occurred. Try again."

@app.route("/save_message", methods=["POST"])
def save_message_route():
    logger.debug("Accessing save_message route")
    if not session.get('logged_in'):
        logger.debug("Unauthorized access to save_message")
        return jsonify({"status": "Unauthorized"})
    try:
        user_id = session.get('user_id')
        message = request.form.get("message")
        is_user = request.form.get("isUser") == "true"
        chat_id = request.form.get("chatId") or session.get('current_chat_id')
        logger.debug(f"Saving message: {message} for user: {user_id}, chat_id: {chat_id}")
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
    logger.debug("Accessing get_history route")
    if not session.get('logged_in'):
        logger.debug("Unauthorized access to get_history")
        return jsonify({"error": "Please log in"})
    try:
        user_id = session.get('user_id')
        chat_id = request.args.get('chatId') or session.get('current_chat_id')
        logger.debug(f"Fetching history for user: {user_id}, chat_id: {chat_id}")
        history = get_chat_history(user_id, chat_id)
        conn = sqlite3.connect('chat_history.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT DISTINCT chat_id FROM chats WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        chat_ids = [row[0] for row in c.fetchall()]
        conn.close()
        return jsonify({"history": history, "chatIds": chat_ids, "currentChatId": chat_id})
    except Exception as e:
        logger.error(f"Error in get_history: {e}")
        return jsonify({"error": "Failed to load history"})

@app.route("/delete_chat_route", methods=["POST"])
def delete_chat_route():
    logger.debug("Accessing delete_chat route")
    if not session.get('logged_in'):
        logger.debug("Unauthorized access to delete_chat")
        return jsonify({"status": "Unauthorized"})
    try:
        user_id = session.get('user_id')
        chat_id = request.form.get("chatId")
        logger.debug(f"Deleting chat: {chat_id} for user: {user_id}")
        if not chat_id:
            return jsonify({"status": "Error", "message": "No chat ID provided"})
        result = delete_chat(user_id, chat_id)
        if result["status"] == "OK" and chat_id == session.get('current_chat_id'):
            session['current_chat_id'] = f"chat_{user_id}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in delete_chat_route: {e}")
        return jsonify({"status": "Error", "message": str(e)})

@app.route("/settings", methods=["GET", "POST"])
def settings():
    logger.debug("Accessing settings route")
    if not session.get('logged_in'):
        logger.debug("Unauthorized access to settings, redirecting to login")
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    user = get_user(user_id)
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        name = request.form.get("name", user['name'] if user else "")
        email = request.form.get("email", user['email'] if user else "")
        two_factor = request.form.get("two_factor") == "on"
        email_notifications = request.form.get("email_notifications") == "on"
        sms_notifications = request.form.get("sms_notifications") == "on"
        security_question1 = request.form.get("security_question1")
        security_answer1 = request.form.get("security_answer1")
        security_question2 = request.form.get("security_question2")
        security_answer2 = request.form.get("security_answer2")
        profile_picture = None

        if user and check_password_hash(user['password'], current_password):
            if new_password and len(new_password) >= 6:
                hashed_password = generate_password_hash(new_password)
            else:
                hashed_password = user['password']

            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename:
                    filename = secure_filename(f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                    file_path = safe_join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    profile_picture = filename

            conn = sqlite3.connect('chat_history.db', check_same_thread=False)
            c = conn.cursor()
            c.execute("UPDATE users SET password = ?, name = ?, email = ?, two_factor_enabled = ?, email_notifications = ?, sms_notifications = ?, security_question1 = ?, security_answer1 = ?, security_question2 = ?, security_answer2 = ?, profile_picture = ? WHERE username = ?",
                      (hashed_password, name, email, two_factor, email_notifications, sms_notifications, security_question1, security_answer1, security_question2, security_answer2, profile_picture or user.get('profile_picture'), user_id))
            conn.commit()
            conn.close()
            encrypt_credentials(user_id, new_password or current_password, name, email, two_factor, email_notifications, sms_notifications, security_question1, security_answer1, security_question2, security_answer2, profile_picture or user.get('profile_picture'))
            logger.debug(f"Settings updated for user: {user_id}")
            return redirect(url_for('settings', success="Settings updated successfully"))
        logger.debug("Settings update failed: Invalid current password")
        return render_template("settings.html", user=user, error="Invalid current password")
    logger.debug("Rendering settings page")
    return render_template("settings.html", user=user)

@app.route("/learn", methods=["POST"])
def learn():
    logger.debug("Accessing learn route")
    if not session.get('logged_in'):
        logger.debug("Unauthorized access to learn")
        return jsonify({"status": "Unauthorized"})
    try:
        question = request.form.get("question")
        answer = request.form.get("answer")
        logger.debug(f"Learning attempt: question={question}, answer={answer}")
        if question and answer and "?" in question:
            response = save_learned_knowledge(question, answer)
            return jsonify({"status": "OK", "response": response})
        return jsonify({"status": "Error", "message": "Invalid input"})
    except Exception as e:
        logger.error(f"Error in learn: {e}")
        return jsonify({"status": "Error", "message": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)