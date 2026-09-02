document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    
    // Auto-scroll to bottom of chat
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Show typing indicator
    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'chat-message bot typing-indicator-wrapper';
        indicator.id = 'typing-indicator';
        indicator.innerHTML = `
            <div class="user-avatar bot-avatar">🤖</div>
            <div class="message-bubble typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        chatMessages.appendChild(indicator);
        scrollToBottom();
    }
    
    // Remove typing indicator
    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    // Append message to chat UI
    function appendMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;
        
        const avatar = sender === 'student' ? '👨‍🎓' : '🤖';
        
        messageDiv.innerHTML = `
            <div class="user-avatar">${avatar}</div>
            <div class="message-bubble">
                <p>${escapeHtml(text).replace(/\n/g, '<br>')}</p>
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }
    
    // Helper to prevent HTML injections
    function escapeHtml(string) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return string.replace(/[&<>"']/g, function(m) { return map[m]; });
    }
    
    // Handle form submit
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const query = chatInput.value.trim();
            if (!query) return;
            
            // Add student message to UI
            appendMessage('student', query);
            chatInput.value = '';
            
            // Show bot typing
            showTypingIndicator();
            
            // Send query to Flask backend
            fetch('/chatbot/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: query })
            })
            .then(res => res.json())
            .then(data => {
                removeTypingIndicator();
                appendMessage('bot', data.answer);
            })
            .catch(err => {
                console.error(err);
                removeTypingIndicator();
                appendMessage('bot', "An error occurred while connecting to the college server. Please try again later.");
            });
        });
    }
    
    // Handle suggestion chips click
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    suggestionChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.textContent.trim().replace(/^"|"$/g, '');
            if (chatInput) {
                chatInput.value = query;
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    });
    
    // Initial scroll
    scrollToBottom();
});
