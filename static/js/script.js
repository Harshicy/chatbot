const backgrounds = ['/static/images/tech-bg.jpg'];

function setRandomBackground() {
    if (window.location.pathname === '/') {
        const randomBg = backgrounds[Math.floor(Math.random() * backgrounds.length)];
        document.body.style.backgroundImage = `url(${randomBg})`;
        document.body.classList.add('bg-animated');
        setTimeout(() => document.body.classList.remove('bg-animated'), 1000);
    }
}

function updateProfileIcon(username) {
    const profileIcon = document.querySelector('.profile-icon');
    if (profileIcon && username && username.length > 0) {
        // No need to set text here as logo is in header
    }
}

function toggleDropdown() {
    const dropdown = document.getElementById('dropdown-content');
    dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('dropdown-content');
    const profileIcon = document.querySelector('.profile-icon');
    if (!profileIcon.contains(event.target) && !dropdown.contains(event.target)) {
        dropdown.style.display = 'none';
    }
});

function loadChat(chatId) {
    fetch(`/get_history?chatId=${encodeURIComponent(chatId)}`)
        .then(response => response.json())
        .then(data => {
            const chatBox = document.querySelector('.chat-box');
            chatBox.innerHTML = '';
            data.history.forEach(msg => {
                const message = document.createElement('div');
                message.classList.add('message', msg.isUser ? 'user-message' : 'bot-message');
                message.textContent = msg.message;
                if (msg.message.includes('\n')) {
                    message.innerHTML = msg.message.replace(/\n/g, '<br>');
                }
                chatBox.appendChild(message);
            });
            chatBox.scrollTop = chatBox.scrollHeight;
            fetch('/save_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `chatId=${encodeURIComponent(chatId)}&message=&isUser=false`
            });
        })
        .catch(error => console.error('Error loading chat:', error));
}

function startNewChat() {
    fetch('/get_response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'message=new chat'
    })
    .then(response => response.text())
    .then(data => {
        const chatBox = document.querySelector('.chat-box');
        const message = document.createElement('div');
        message.classList.add('message', 'bot-message');
        message.textContent = data;
        chatBox.appendChild(message);
        chatBox.scrollTop = chatBox.scrollHeight;
        location.reload();
    })
    .catch(error => console.error('Error starting new chat:', error));
}

function deleteChat(chatId) {
    if (confirm(`Are you sure you want to delete chat ${chatId}?`)) {
        fetch('/delete_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `chatId=${encodeURIComponent(chatId)}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'OK') {
                location.reload();
            } else {
                alert(data.message);
            }
        })
        .catch(error => console.error('Error deleting chat:', error));
    }
}

document.addEventListener('DOMContentLoaded', () => {
    setRandomBackground();
    updateProfileIcon(username);

    const menuIcon = document.querySelector('.menu-icon');
    const sidebar = document.querySelector('.sidebar');
    const closeBtn = document.querySelector('.closebtn');

    if (menuIcon && sidebar && closeBtn) {
        menuIcon.addEventListener('click', () => {
            sidebar.style.width = '250px';
        });

        closeBtn.addEventListener('click', () => {
            sidebar.style.width = '0';
        });
    }

    const input = document.querySelector('#message-input');
    const sendButton = document.querySelector('button.send');
    const chatBox = document.querySelector('.chat-box');

    if (input && sendButton && chatBox) {
        sendButton.addEventListener('click', (e) => {
            e.preventDefault();
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
                    if (data.includes('\n')) {
                        botMessage.innerHTML = data.replace(/\n/g, '<br>');
                    }
                    chatBox.appendChild(botMessage);
                    chatBox.scrollTop = chatBox.scrollHeight;
                })
                .catch(error => {
                    console.error('Error:', error);
                    const errorMessage = document.createElement('div');
                    errorMessage.classList.add('message', 'bot-message');
                    errorMessage.textContent = 'Error processing your request. Please try again.';
                    chatBox.appendChild(errorMessage);
                    chatBox.scrollTop = chatBox.scrollHeight;
                });
                input.value = '';
            }
        });

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && input.value.trim()) {
                sendButton.click();
            }
        });
    }

    if (chatBox && currentChatId) {
        loadChat(currentChatId);
    }

    // Notify user if OpenAI is unavailable
    if (!openaiAvailable) {
        const notice = document.createElement('div');
        notice.classList.add('message', 'bot-message');
        notice.textContent = 'Note: Advanced AI features are unavailable. Please install the OpenAI module and set the API key in .env.';
        document.querySelector('.chat-box').appendChild(notice);
    }
});