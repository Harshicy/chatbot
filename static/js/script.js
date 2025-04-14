// Backgrounds array (adjust paths based on your static file structure)
const backgrounds = ['/static/images/tech-bg.jpg'];

// Set random background for the homepage
function setRandomBackground() {
    if (window.location.pathname === '/' || window.location.pathname === '/index') {
        const randomBg = backgrounds[Math.floor(Math.random() * backgrounds.length)];
        document.body.style.backgroundImage = `url(${randomBg})`;
        document.body.classList.add('bg-animated');
        setTimeout(() => document.body.classList.remove('bg-animated'), 1000);
    }
}

// Update profile icon (placeholder, adjust if using an image)
function updateProfileIcon(username) {
    const profileIcon = document.querySelector('.profile-icon');
    if (profileIcon && username && username.length > 0) {
        // Optional: Set initial text or image if needed
        // profileIcon.textContent = username.charAt(0).toUpperCase();
    }
}

// Toggle sidebar functionality
function toggleNav() {
    const sidebar = document.getElementById("sidebar");
    const chatContainer = document.querySelector(".chat-container");
    if (sidebar && chatContainer) {
        if (sidebar.style.width === "250px") {
            closeNav();
        } else {
            sidebar.style.width = "250px";
            chatContainer.style.marginLeft = "250px";
        }
    }
}

function closeNav() {
    const sidebar = document.getElementById("sidebar");
    const chatContainer = document.querySelector(".chat-container");
    if (sidebar && chatContainer) {
        sidebar.style.width = "0";
        chatContainer.style.marginLeft = "0";
    }
}

// Toggle dropdown menu
function toggleDropdown(event) {
    event.preventDefault();
    event.stopPropagation();
    const dropdown = document.getElementById('dropdown-content');
    if (dropdown) {
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('dropdown-content');
    const profileIcon = document.querySelector('.profile-icon');
    if (dropdown && profileIcon && !profileIcon.contains(event.target) && !dropdown.contains(event.target)) {
        dropdown.style.display = 'none';
    }
});

// Perform logout
function logout() {
    fetch('{{ url_for('logout') }}', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    .then(response => {
        if (response.ok) {
            window.location.href = '{{ url_for('login') }}';
        } else {
            alert('Logout failed. Please try again.');
        }
    })
    .catch(error => console.error('Error during logout:', error));
}

// Load chat history
function loadChat(chatId) {
    fetch(`{{ url_for('get_history') }}?chatId=${encodeURIComponent(chatId)}`)
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            const chatBox = document.querySelector('.chat-box');
            if (chatBox) {
                chatBox.innerHTML = '';
                data.history.forEach(msg => {
                    const message = document.createElement('div');
                    message.classList.add('message', msg.isUser ? 'user-message' : 'bot-message');
                    message.innerHTML = msg.message.replace(/\n/g, '<br>');
                    chatBox.appendChild(message);
                });
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        })
        .catch(error => console.error('Error loading chat:', error));
}

// Start new chat
function startNewChat() {
    const newChatId = `chat_{{ user_id | default('guest') }}_${new Date().toISOString().replace(/[:.-]/g, '_')}`;
    fetch('{{ url_for('get_response_route') }}', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `message=new chat&chatId=${encodeURIComponent(newChatId)}`
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.text();
    })
    .then(response => {
        const chatBox = document.querySelector('.chat-box');
        if (chatBox) {
            chatBox.innerHTML = '';
            const botMsg = document.createElement('div');
            botMsg.classList.add('message', 'bot-message');
            botMsg.innerHTML = response.replace(/\n/g, '<br>');
            chatBox.appendChild(botMsg);
            chatBox.scrollTop = chatBox.scrollHeight;
            // Update the sidebar with the new chat
            const sidebar = document.getElementById('sidebar');
            if (sidebar) {
                const newChatLink = document.createElement('a');
                newChatLink.href = '#';
                newChatLink.onclick = () => loadChat(newChatId);
                newChatLink.textContent = newChatId;
                sidebar.insertBefore(newChatLink, sidebar.lastElementChild);
                const deleteLink = document.createElement('a');
                deleteLink.href = '#';
                deleteLink.onclick = () => deleteChat(newChatId);
                deleteLink.textContent = 'Delete';
                deleteLink.style.color = '#ff4444';
                sidebar.insertBefore(deleteLink, sidebar.lastElementChild);
            }
        }
    })
    .catch(error => console.error('Error starting new chat:', error));
}

// Delete chat
function deleteChat(chatId) {
    if (confirm(`Are you sure you want to delete chat ${chatId}?`)) {
        fetch('{{ url_for('delete_chat_route') }}', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `chatId=${encodeURIComponent(chatId)}`
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            const chatBox = document.querySelector('.chat-box');
            if (data.status === 'OK' && chatBox) {
                chatBox.innerHTML = '<div class="message bot-message">Chat deleted. Start a new chat.</div>';
                chatBox.scrollTop = chatBox.scrollHeight;
                // Remove the chat from the sidebar
                const sidebar = document.getElementById('sidebar');
                if (sidebar) {
                    const chatLinks = sidebar.getElementsByTagName('a');
                    for (let i = 0; i < chatLinks.length; i++) {
                        if (chatLinks[i].textContent === chatId || chatLinks[i].textContent === 'Delete') {
                            sidebar.removeChild(chatLinks[i].parentNode || chatLinks[i]);
                            i--; // Adjust index after removal
                        }
                    }
                }
            } else if (chatBox) {
                alert(data.message || 'Failed to delete chat');
            }
        })
        .catch(error => console.error('Error deleting chat:', error));
    }
}

// DOM Content Loaded event
document.addEventListener('DOMContentLoaded', () => {
    setRandomBackground();
    updateProfileIcon('{{ user_id | default('') }}');

    // Sliding menu functionality
    const menuIcon = document.querySelector('.menu-icon');
    const sidebar = document.getElementById("sidebar");
    const closeBtn = document.querySelector('.closebtn');
    const chatContainer = document.querySelector('.chat-container');

    if (menuIcon && sidebar && closeBtn && chatContainer) {
        menuIcon.addEventListener('click', toggleNav);
        closeBtn.addEventListener('click', closeNav);
    }

    // Chat input and send functionality
    const input = document.querySelector('#message-input');
    const sendButton = document.querySelector('button.send');
    const chatBox = document.querySelector('.chat-box');

    if (input && sendButton && chatBox) {
        sendButton.addEventListener('click', (e) => {
            e.preventDefault();
            const messageText = input.value.trim();
            if (messageText) {
                const userMsg = document.createElement('div');
                userMsg.classList.add('message', 'user-message');
                userMsg.innerHTML = messageText.replace(/\n/g, '<br>');
                chatBox.appendChild(userMsg);
                chatBox.scrollTop = chatBox.scrollHeight;

                fetch('{{ url_for('get_response_route') }}', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `message=${encodeURIComponent(messageText)}&chatId={{ current_chat_id | default('') | urlencode }}`
                })
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.text();
                })
                .then(response => {
                    const botMsg = document.createElement('div');
                    botMsg.classList.add('message', 'bot-message');
                    botMsg.innerHTML = response.replace(/\n/g, '<br>');
                    chatBox.appendChild(botMsg);
                    chatBox.scrollTop = chatBox.scrollHeight;
                })
                .catch(error => {
                    console.error('Error:', error);
                    const errorMsg = document.createElement('div');
                    errorMsg.classList.add('message', 'bot-message');
                    errorMsg.textContent = 'Error processing your request. Please try again.';
                    chatBox.appendChild(errorMsg);
                    chatBox.scrollTop = chatBox.scrollHeight);
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

    // Initialize with current chat if logged in and on chat page
    const chatBoxExists = document.querySelector('.chat-box');
    if (chatBoxExists && '{{ current_chat_id | default('') }}' && '{{ logged_in }}' === 'True') {
        loadChat('{{ current_chat_id | default('') }}');
    }

    // Notify user if OpenAI is unavailable
    if (!{{ openai_available | tojson }} && chatBoxExists) {
        const notice = document.createElement('div');
        notice.classList.add('message', 'bot-message');
        notice.textContent = 'Note: Advanced AI features are unavailable. Please install the OpenAI module and set the API key in .env.';
        chatBoxExists.appendChild(notice);
    }
});