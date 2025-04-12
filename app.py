from flask import Flask, render_template, request, jsonify
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
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, user_id TEXT, message TEXT, is_user INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_response", methods=["POST"])
def get_response():
    user_message = request.form.get("message")
    user_id = request.form.get("userId")
    if user_message:
        response = chatbot.respond(user_message)
        save_message(user_id, user_message, True)
        save_message(user_id, response, False)
        return response
    return "No message provided"

@app.route("/save_message", methods=["POST"])
def save_message():
    user_id = request.form.get("userId")
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
    user_id = request.args.get("userId")
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT timestamp, message, is_user FROM messages WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    history = [{"timestamp": row[0], "message": row[1], "isUser": bool(row[2])} for row in c.fetchall()]
    conn.close()
    return jsonify(history)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")  # In production, use hashing (e.g., bcrypt)
        if username and password:  # Simple validation; enhance with a real database
            user_id = username  # Use username as user_id for simplicity
            localStorage.setItem('userId', user_id)  # This would be server-side in a real app
            return render_template("index.html", logged_in=True, user_id=user_id)
    return '''
        <form method="POST">
            <label>Username: <input type="text" name="username"></label><br>
            <label>Password: <input type="password" name="password"></label><br>
            <button type="submit">Login</button>
        </form>
        <p>Not implemented yet; use guest mode for now.</p>
    '''

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)