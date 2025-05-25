document.addEventListener('DOMContentLoaded', () => {
    let currentGroupId = null;
    const chatMessages = document.getElementById('chatMessages');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendMessage');

    // Load groups
    fetch('/get_groups')
        .then(response => response.json())
        .then(groups => populateGroups(groups));

    // Handle group selection
    document.querySelector('.skupine-list').addEventListener('click', (e) => {
        if (e.target.classList.contains('skupina-item')) {
            currentGroupId = e.target.dataset.groupId;
            loadMessages(currentGroupId);
        }
    });

    // Send message
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    function populateGroups(groups) {
        const groupList = document.querySelector('.skupine-list');
        groupList.innerHTML = groups.map(group => `
            <div class="skupina-item" data-group-id="${group.id}">
                ${group.name}
            </div>
        `).join('');
    }

    function loadMessages(groupId) {
        fetch(`/get_messages/${groupId}`)
            .then(response => response.json())
            .then(messages => {
                chatMessages.innerHTML = messages.map(msg => `
                    <div class="message">
                        <span class="message-time">${msg.time}</span>
                        <span class="message-content">${msg.content}</span>
                    </div>
                `).join('');
                chatMessages.scrollTop = chatMessages.scrollHeight;
            });
    }

    function sendMessage() {
        const content = messageInput.value.trim();
        if (!content || !currentGroupId) return;

        fetch('/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                group_id: currentGroupId,
                content: content
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                messageInput.value = '';
                loadMessages(currentGroupId);
            }
        });
    }
});