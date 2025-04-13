// Random Background Images (only for chatbot)
const backgrounds = [
    '/static/images/tech-bg.jpg'
];

function setRandomBackground() {
    const randomBg = backgrounds[Math.floor(Math.random() * backgrounds.length)];
    document.body.style.backgroundImage = `url(${randomBg})`;
    document.body.classList.add('bg-animated');
    setTimeout(() => document.body.classList.remove('bg-animated'), 1000);
}

// Set initial background on page load only
document.addEventListener('DOMContentLoaded', () => {
    setRandomBackground();
    const username = '{{ session["user_id"] }}'; // Flask template syntax
    updateProfileIcon(username);

    // Add "H" logo
    const chatContainer = document.querySelector('.chat-container');
    const logo = document.createElement('div');
    logo.className = 'logo';
    logo.textContent = 'H';
    chatContainer.insertBefore(logo, chatContainer.firstChild);

    // Sliding Menu Logic
    const menuIcon = document.querySelector('.menu-icon');
    const sidebar = document.querySelector('.sidebar');
    const closeBtn = document.querySelector('.closebtn');

    menuIcon.addEventListener('click', () => {
        sidebar.style.width = '250px';
    });

    closeBtn.addEventListener('click', () => {
        sidebar.style.width = '0';
    });

    // Chat Input Handling with Enter Key
    const input = document.querySelector('input[type="text"]');
    const sendButton = document.querySelector('button.send');
    const chatBox = document.querySelector('.chat-box');

    sendButton.addEventListener('click', () => {
        if (input.value.trim()) {
            const message = document.createElement('div');
            message.classList.add('message', 'user-message');
            message.textContent = input.value.trim();
            chatBox.appendChild(message);
            chatBox.scrollTop = chatBox.scrollHeight;
            fetch('/get_response', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `message=${encodeURIComponent(input.value.trim())}`
            })
            .then(response => response.text())
            .then(data => {
                const botMessage = document.createElement('div');
                botMessage.classList.add('message', 'bot-message');
                botMessage.textContent = data;
                chatBox.appendChild(botMessage);
                chatBox.scrollTop = chatBox.scrollHeight;
            })
            .catch(error => console.error('Error:', error));
            input.value = '';
        }
    });

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && input.value.trim()) {
            sendButton.click();
        }
    });

    // Load history once on page load
    function loadHistory() {
        fetch('/get_history?chatId={{ current_chat_id }}')
            .then(response => response.json())
            .then(data => {
                chatBox.innerHTML = '';
                data.history.forEach(msg => {
                    const message = document.createElement('div');
                    message.classList.add('message', msg.isUser ? 'user-message' : 'bot-message');
                    message.textContent = msg.message;
                    chatBox.appendChild(message);
                });
                chatBox.scrollTop = chatBox.scrollHeight;
            });
    }
    loadHistory();
});

// Profile Icon Letter
function updateProfileIcon(username) {
    const profileIcon = document.querySelector('.profile-icon');
    if (username && username.length > 0) {
        profileIcon.textContent = username[0].toUpperCase();
    }
}