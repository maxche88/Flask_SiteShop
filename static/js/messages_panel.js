document.addEventListener('DOMContentLoaded', function () {
    // DOM элементы
    const dialogsList = document.getElementById('dialogs-list');
    const dialogRowTemplate = document.getElementById('dialog-row-template');
    const chatModal = document.getElementById('chat-modal');
    const chatMessagesContainer = document.getElementById('chat-messages-container');
    const modalDialogId = document.getElementById('modal-dialog-id');
    const closeChatModalBtn = document.getElementById('close-chat-modal');
    const chatMessageInput = document.getElementById('chat-message-input');
    const sendChatMessageBtn = document.getElementById('send-chat-message');
    const infoPanel = document.getElementById('messages-info-panel');

    let currentDialogId = null;

    // === Утилиты ===
    function showMessage(message, type = 'info') {
        if (infoPanel) {
            infoPanel.textContent = message;
            infoPanel.className = `messages-info ${type}`;
            infoPanel.classList.remove('hidden');
            setTimeout(() => infoPanel.classList.add('hidden'), 5000);
        }
    }

    function formatDate(dateString) {
        if (!dateString) return '—';
        const date = new Date(dateString);
        return date.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function getRoleLabel(role) {
        const labels = {
            'admin': 'Админ',
            'suser': 'Менеджер',
            'user': 'Пользователь',
            'guest': 'Гость'
        };
        return labels[role] || role;
    }

    function getRoleClass(role) {
        return ['admin', 'suser', 'user', 'guest'].includes(role) ? role : 'user';
    }

    // === 1. Загрузка списка диалогов ===
    async function loadDialogs() {
        try {
            const response = await fetch('/api/chat/dialogs', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const dialogs = await response.json();
            renderDialogs(dialogs);
        } catch (error) {
            console.error('Ошибка загрузки диалогов:', error);
            showMessage('Не удалось загрузить список диалогов.', 'error');
        }
    }

    function renderDialogs(dialogs) {
        dialogsList.innerHTML = '';

        if (!dialogs || dialogs.length === 0) {
            dialogsList.innerHTML = `
                <div class="dialog-item" style="grid-column: 1 / -1; text-align: center; padding: 20px; color: #666;">
                    Нет доступных диалогов
                </div>
            `;
            return;
        }

        dialogs.forEach(dialog => {
            const row = dialogRowTemplate.content.cloneNode(true);
            const item = row.querySelector('.dialog-item');

            item.dataset.dialogId = dialog.id;

            item.querySelector('.id-col').textContent = dialog.id;
            item.querySelector('.topic-col').textContent = dialog.topic_name || '—';
            
            const client = dialog.name && dialog.email
                ? `${dialog.name} (${dialog.email})`
                : (dialog.name || '—');
            item.querySelector('.client-col').textContent = client;

            const context = dialog.order_id 
                ? `Заказ #${dialog.order_id}` 
                : (dialog.product_id ? `Товар ID: ${dialog.product_id}` : '—');

            item.querySelector('.context-col').textContent = context;

            const statusEl = item.querySelector('.status-col');
            statusEl.textContent = dialog.status === 'open' ? 'Открыт' : 'Закрыт';
            statusEl.classList.add(dialog.status);

            item.querySelector('.updated-col').textContent = formatDate(dialog.updated_at);
            item.querySelector('.count-col').textContent = dialog.message_count || 0;
            item.querySelector('.last-sender-col').textContent = getRoleLabel(dialog.last_sender_role) || '—';

            item.addEventListener('click', () => openChatModal(dialog.id));
            dialogsList.appendChild(item);
        });
    }

    // === 2. Открытие модального окна ===
    async function openChatModal(dialogId) {
        currentDialogId = dialogId;
        modalDialogId.textContent = dialogId;
        chatMessagesContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#777;">Загрузка...</div>';
        chatModal.classList.remove('hidden');
        chatMessageInput.value = '';
        chatMessageInput.focus();

        try {
            const response = await fetch(`/api/chat/dialogs/${dialogId}/messages`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const messages = await response.json();
            renderMessages(messages);
        } catch (error) {
            console.error(`Ошибка загрузки сообщений диалога ${dialogId}:`, error);
            chatMessagesContainer.innerHTML = '<div style="color:red; padding:10px;">Не удалось загрузить сообщения.</div>';
        }
    }

    function renderMessages(messages) {
        chatMessagesContainer.innerHTML = '';

        if (!messages || messages.length === 0) {
            chatMessagesContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#777;">Нет сообщений</div>';
            return;
        }

        messages.forEach(msg => {
            const roleClass = getRoleClass(msg.sender_role);
            const messageEl = document.createElement('div');
            messageEl.className = `message-entry ${roleClass}`;
            messageEl.innerHTML = `
                <div class="message-header">
                    <span class="message-sender">${getRoleLabel(msg.sender_role)}</span>
                    <span class="message-timestamp">${formatDate(msg.created_at)}</span>
                </div>
                <div class="message-text">${escapeHtml(msg.text)}</div>
            `;
            chatMessagesContainer.appendChild(messageEl);
        });

        // Прокрутка вниз
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    // Защита от XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // === 3. Отправка нового сообщения ===
    async function sendNewMessage() {
        const text = chatMessageInput.value.trim();
        if (!text) {
            showMessage('Сообщение не может быть пустым.', 'warning');
            return;
        }

        if (!currentDialogId) {
            showMessage('Ошибка: диалог не выбран.', 'error');
            return;
        }

        const sendBtn = sendChatMessageBtn;
        const originalText = sendBtn.textContent;
        sendBtn.textContent = 'Отправка...';
        sendBtn.disabled = true;

        try {
            const response = await fetch(`/api/chat/dialogs/${currentDialogId}/reply`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    text: text,
                    sender_role: window.CURRENT_USER_ROLE // 'suser' или 'admin'
                })
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.message || `HTTP ${response.status}`);
            }

            // Очистка поля
            chatMessageInput.value = '';
            chatMessageInput.focus();

            // Перезагрузка сообщений (или можно добавить вручную)
            const res = await fetch(`/api/chat/dialogs/${currentDialogId}/messages`);
            const messages = await res.json();
            renderMessages(messages);

        } catch (error) {
            console.error('Ошибка отправки сообщения:', error);
            showMessage(`Ошибка: ${error.message || 'неизвестная'}`, 'error');
        } finally {
            sendBtn.textContent = originalText;
            sendBtn.disabled = false;
        }
    }

    // === Обработчики событий ===
    closeChatModalBtn.addEventListener('click', () => {
        chatModal.classList.add('hidden');
        currentDialogId = null;
    });

    chatModal.querySelector('.chat-modal-overlay').addEventListener('click', (e) => {
        if (e.target === chatModal.querySelector('.chat-modal-overlay')) {
            chatModal.classList.add('hidden');
            currentDialogId = null;
        }
    });

    sendChatMessageBtn.addEventListener('click', sendNewMessage);

    chatMessageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendNewMessage();
        }
    });

    // === Запуск ===
    loadDialogs();
});