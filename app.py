from flask import Flask, render_template, request
import nltk
from nltk.chat.util import Chat, reflections

# Download required NLTK data
nltk.download('punkt')

app = Flask(__name__)

# Define chatbot conversation pairs
pairs = [
    [r"hi|hello|hey", ["Hello!", "Hi there!", "Hey! How can I help you?"]],
    [r"how are you", ["I'm doing great, thanks! How about you?", "As an AI, I'm always good!"]],
    [r"what is your name", ["I'm Grok, nice to meet you!", "My name is Grok, created by xAI"]],
    [r"bye|goodbye", ["See you later!", "Goodbye!", "Have a great day!"]],
    [r"(.*) weather (.*)", ["I'm not a weather bot, but I can chat about other things!"]],
    [r"(.*)", ["Interesting! Tell me more.", "Can you clarify that?", "I'm listening..."]]
]

# Create chatbot instance
chatbot = Chat(pairs, reflections)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_response", methods=["POST"])
def get_response():
    user_message = request.form["message"]
    print(f"Received message: {user_message}")  # Debug print
    response = chatbot.respond(user_message)
    print(f"Returning response: {response}")    # Debug print
    return response

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)