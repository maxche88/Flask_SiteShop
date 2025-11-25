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
    let isGuestDialog = false;

    // === Чекбоксы для выбора диалогов ===
    document.getElementById('select-all-dialogs').addEventListener('change', function () {
        const isChecked = this.checked;
        document.querySelectorAll('.dialog-checkbox').forEach(checkbox => {
            checkbox.checked = isChecked;
        });
    });

    document.getElementById('dialogs-list').addEventListener('change', function (e) {
        if (e.target.classList.contains('dialog-checkbox')) {
            const allCheckboxes = document.querySelectorAll('.dialog-checkbox');
            const checkedCheckboxes = document.querySelectorAll('.dialog-checkbox:checked');
            document.getElementById('select-all-dialogs').checked = (allCheckboxes.length === checkedCheckboxes.length);
        }
    });

    function getSelectedDialogIds() {
        const selected = [];
        document.querySelectorAll('.dialog-checkbox:checked').forEach(checkbox => {
            const row = checkbox.closest('.dialog-item');
            if (row) {
                const id = row.dataset.dialogId;
                if (id) selected.push(parseInt(id, 10));
            }
        });
        return selected;
    }

    // Выпадающее меню статуса
    const changeStatusBtn = document.getElementById('change-status-btn');
    const statusDropdown = document.getElementById('status-dropdown');

    changeStatusBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        statusDropdown.classList.toggle('hidden');
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.status-dropdown-wrapper')) {
            statusDropdown.classList.add('hidden');
        }
    });

    statusDropdown.addEventListener('click', async (e) => {
        if (e.target.classList.contains('status-option')) {
            const newStatus = e.target.dataset.status;
            const dialogIds = getSelectedDialogIds();

            if (dialogIds.length === 0) {
                showMessage('Выберите хотя бы один диалог', 'warning');
                return;
            }

            statusDropdown.classList.add('hidden');

            try {
                const response = await fetch('/api/chat/dialogs/bulk-update-status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        dialog_ids: dialogIds,
                        status: newStatus
                    })
                });

                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.error || 'Не удалось обновить статус');
                }

                showMessage(`Статус обновлён на "${newStatus}" для ${dialogIds.length} диалогов`, 'success');
                loadDialogs();

            } catch (error) {
                console.error('Ошибка обновления статуса:', error);
                showMessage(`Ошибка: ${error.message}`, 'error');
            }
        }
    });

    function updateStatusButtonState() {
        const hasSelected = getSelectedDialogIds().length > 0;
        changeStatusBtn.disabled = !hasSelected;
    }

    document.getElementById('select-all-dialogs').addEventListener('change', updateStatusButtonState);
    document.getElementById('dialogs-list').addEventListener('change', updateStatusButtonState);

    // Удаление диалогов
    const deleteDialogsBtn = document.getElementById('delete-dialogs-btn');

    function updateDeleteButtonState() {
        const hasSelected = getSelectedDialogIds().length > 0;
        deleteDialogsBtn.disabled = !hasSelected;
    }

    document.getElementById('select-all-dialogs').addEventListener('change', updateDeleteButtonState);
    document.getElementById('dialogs-list').addEventListener('change', updateDeleteButtonState);

    deleteDialogsBtn.addEventListener('click', async () => {
        const dialogIds = getSelectedDialogIds();
        if (dialogIds.length === 0) return;

        if (!confirm(`Вы уверены, что хотите удалить ${dialogIds.length} диалог(ов)? Это действие нельзя отменить.`)) {
            return;
        }

        try {
            const response = await fetch('/api/chat/dialogs/bulk-delete', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ dialog_ids: dialogIds })
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.error || 'Не удалось удалить диалоги');
            }

            showMessage(`Удалено ${dialogIds.length} диалог(ов)`, 'success');
            loadDialogs();

        } catch (error) {
            console.error('Ошибка удаления диалогов:', error);
            showMessage(`Ошибка: ${error.message}`, 'error');
        }
    });

    // Утилиты
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

    // Загрузка списка диалогов
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
            dialogsList.innerHTML = '';
            showMessage('Нет доступных диалогов', 'info');
            return;
        }

        dialogs.forEach(dialog => {
            const row = dialogRowTemplate.content.cloneNode(true);
            const item = row.querySelector('.dialog-item');

            item.dataset.dialogId = dialog.id;
            item.dataset.userId = dialog.user_id; // Сохраняем user_id

            item.querySelector('.id-col').textContent = dialog.id;
            item.querySelector('.topic-col').textContent = dialog.topic_name || '—';
            
            const usernameEl = item.querySelector('.username');
            if (dialog.user_id != null && dialog.username) {
                usernameEl.textContent = dialog.username;
            } else {
                usernameEl.textContent = 'Гость';
            }

            const emailEl = item.querySelector('.client-col');
            emailEl.textContent = dialog.email || '—';

            const context = dialog.order_id 
                ? `Заказ #${dialog.order_id}` 
                : (dialog.product_id ? `Товар ID: ${dialog.product_id}` : '—');

            item.querySelector('.context-col').textContent = context;

            const statusEl = item.querySelector('.status-col');
            statusEl.textContent = 
                dialog.status === 'open' ? 'Открыт' :
                dialog.status === 'closed' ? 'Закрыт' : 'Архив';
            statusEl.className = 'dialogs-col status-col ' + dialog.status;

            item.querySelector('.updated-col').textContent = formatDate(dialog.updated_at);
            item.querySelector('.count-col').textContent = dialog.message_count || 0;
            item.querySelector('.last-sender-col').textContent = getRoleLabel(dialog.last_sender_role) || '—';

            if (dialog.unread_count > 0) {
                item.classList.add('has-unread');
            }

            item.addEventListener('click', (e) => {
                if (e.target.closest('.dialog-checkbox')) {
                    return;
                }
                openChatModal(dialog.id);
            });
            dialogsList.appendChild(item);
        });
    }

    // Открытие модального окна
    async function openChatModal(dialogId) {
        currentDialogId = dialogId;
        modalDialogId.textContent = dialogId;
        chatMessagesContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#777;">Загрузка...</div>';
        chatModal.classList.remove('hidden');
        chatMessageInput.value = '';
        chatMessageInput.focus();

        try {
            // Определяем, гость ли (user_id === null)
            const dialogRow = document.querySelector(`.dialog-item[data-dialog-id="${dialogId}"]`);
            isGuestDialog = dialogRow ? (dialogRow.dataset.userId === 'null') : false;

            const response = await fetch(`/api/chat/dialogs/${dialogId}/messages`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const messages = await response.json();
            renderMessages(messages);

            // Обновляем текст кнопки
            if (sendChatMessageBtn) {
                sendChatMessageBtn.textContent = isGuestDialog ? 'Отправить на email' : 'Отправить';
            }

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
            const isSent = msg.sender_role === window.CURRENT_USER_ROLE;
            const senderLabel = getRoleLabel(msg.sender_role);

            const messageEl = document.createElement('div');
            messageEl.className = `chat-message ${isSent ? 'sent' : 'received'}`;
            messageEl.innerHTML = `
                <div class="author">${escapeHtml(senderLabel)}</div>
                <div class="text">${escapeHtml(msg.text)}</div>
                <div class="timestamp">${formatDate(msg.created_at)}</div>
            `;
            chatMessagesContainer.appendChild(messageEl);
        });

        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Отправка нового сообщения
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
                    sender_role: window.CURRENT_USER_ROLE
                })
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.message || `HTTP ${response.status}`);
            }

            chatMessageInput.value = '';
            chatMessageInput.focus();

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

    // Закрытие чата — сброс флага
    function closeChatModal() {
        chatModal.classList.add('hidden');
        if (currentDialogId) {
            const dialogRow = document.querySelector(`.dialog-item[data-dialog-id="${currentDialogId}"]`);
            if (dialogRow) {
                dialogRow.classList.remove('has-unread');
            }
            currentDialogId = null;
            isGuestDialog = false;
        }
    }

    closeChatModalBtn.addEventListener('click', closeChatModal);
    chatModal.querySelector('.chat-modal-overlay').addEventListener('click', (e) => {
        if (e.target === chatModal.querySelector('.chat-modal-overlay')) {
            closeChatModal();
        }
    });

    sendChatMessageBtn.addEventListener('click', sendNewMessage);

    chatMessageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendNewMessage();
        }
    });

    loadDialogs();
});