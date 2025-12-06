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


    // === Темы сообщений ===
    const topicsModal = document.getElementById('topics-modal');
    const closeTopicsModalBtn = document.getElementById('close-topics-modal');
    const topicsTableBody = document.getElementById('topics-table-body');
    const addTopicBtn = document.getElementById('add-topic-btn');

    let editingCell = null;

    let currentDialogId = null;
    let currentDialogStatus = null;
    let isGuestDialog = false;

    // === Чекбоксы и прочая логика ===
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
                const response = await fetch('/api/chat/dialogs/dialog-status_update', {
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
            const response = await fetch('/api/chat/dialogs/dialog-delete', {
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

    // Открытие модалки тем
    document.getElementById('mess-topics-btn').addEventListener('click', async () => {
        topicsModal.classList.remove('hidden');
        await loadTopics();
    });

    // Закрытие модалки
    closeTopicsModalBtn.addEventListener('click', () => {
        topicsModal.classList.add('hidden');
    });

    topicsModal.querySelector('.topics-modal-overlay').addEventListener('click', (e) => {
        if (e.target === topicsModal.querySelector('.topics-modal-overlay')) {
            topicsModal.classList.add('hidden');
        }
    });

    // Загрузка тем
    async function loadTopics() {
        try {
            const response = await fetch('/api/chat/topics', {
                method: 'GET',
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Не удалось загрузить темы');
            const topics = await response.json();
            renderTopics(topics);
        } catch (err) {
            console.error('Ошибка загрузки тем:', err);
            topicsTableBody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:red;">Ошибка загрузки</td></tr>';
        }
    }

    // Отображение тем
    function renderTopics(topics) {
        topicsTableBody.innerHTML = '';
        if (topics.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="4" style="text-align:center;color:#777;">Нет тем</td>`;
            topicsTableBody.appendChild(row);
            return;
        }

        topics.forEach(topic => {
            const row = document.createElement('tr');
            row.dataset.topicId = topic.id;

            const isActiveHtml = `
                <input type="checkbox" ${topic.is_active ? 'checked' : ''} data-field="is_active">
            `;

            row.innerHTML = `
                <td>${topic.id}</td>
                <td class="editable" data-field="name">${escapeHtml(topic.name)}</td>
                <td class="editable" data-field="description">${escapeHtml(topic.description || '')}</td>
                <td>${isActiveHtml}</td>
            `;
            topicsTableBody.appendChild(row);
        });

        // Навешиваем обработчики
        topicsTableBody.querySelectorAll('.editable').forEach(cell => {
            cell.addEventListener('click', startEditing);
        });

        topicsTableBody.querySelectorAll('input[type="checkbox"][data-field="is_active"]').forEach(cb => {
            cb.addEventListener('change', function () {
                const row = this.closest('tr');
                const topicId = row.dataset.topicId;
                const value = this.checked;
                saveTopicField(topicId, 'is_active', value);
            });
        });
    }

    // Начало редактирования
    function startEditing(e) {
        if (editingCell) return; // Защита от нескольких одновременных редактирований

        const cell = e.target;
        const field = cell.dataset.field;
        const currentValue = cell.textContent;

        editingCell = cell;

        const input = document.createElement('input');
        input.type = field === 'description' ? 'text' : 'text';
        input.value = currentValue;
        input.className = 'inline-edit-input';
        input.style.width = '100%';
        input.style.padding = '4px';
        input.style.border = '1px solid #ccc';
        input.style.borderRadius = '3px';

        cell.innerHTML = '';
        cell.appendChild(input);
        input.focus();

        const save = () => {
            const newValue = input.value.trim();
            const row = cell.closest('tr');
            const topicId = row.dataset.topicId;

            if (newValue !== currentValue) {
                saveTopicField(topicId, field, newValue);
            }

            // Вернуть обратно текст
            cell.textContent = escapeHtml(newValue || '');
            editingCell = null;
        };

        input.addEventListener('blur', save);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                save();
                input.blur();
            }
        });
    }

    // Сохранение одного поля темы
    async function saveTopicField(topicId, field, value) {
        try {
            const response = await fetch(`/api/chat/topics/${topicId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ [field]: value })
            });
            if (!response.ok) {
                throw new Error('Не удалось сохранить');
            }
            // Успешно — можно ничего не делать, т.к. UI уже обновлён
        } catch (err) {
            console.error('Ошибка сохранения:', err);
            showMessage(`Ошибка сохранения: ${err.message}`, 'error');
        }
    }

    // Добавление новой темы
    addTopicBtn.addEventListener('click', async () => {
        const newRow = document.createElement('tr');
        newRow.dataset.topicId = 'new'; // временный ID

        newRow.innerHTML = `
            <td>—</td>
            <td class="editable" data-field="name"></td>
            <td class="editable" data-field="description"></td>
            <td><input type="checkbox" checked data-field="is_active"></td>
        `;

        topicsTableBody.appendChild(newRow);

        // Активируем редактирование в имени
        const nameCell = newRow.querySelector('[data-field="name"]');
        nameCell.click();

        // Обработчик для чекбокса (сохранение при изменении)
        const cb = newRow.querySelector('input[type="checkbox"]');
        cb.addEventListener('change', async () => {
            // Создаём тему при первом изменении
            const name = newRow.querySelector('[data-field="name"]').textContent.trim();
            if (!name) return;

            try {
                const res = await fetch('/api/chat/topics', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        name: name,
                        description: newRow.querySelector('[data-field="description"]').textContent.trim(),
                        is_active: cb.checked
                    })
                });
                if (!res.ok) throw new Error('Не удалось создать тему');
                const saved = await res.json();
                newRow.dataset.topicId = saved.id;
                newRow.querySelector('td:first-child').textContent = saved.id;
                showMessage('Тема добавлена', 'success');
            } catch (err) {
                console.error('Ошибка создания темы:', err);
                showMessage(`Ошибка: ${err.message}`, 'error');
                newRow.remove();
            }
        });
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
            showMessage('Нет доступных диалогов', 'info');
            return;
        }

        dialogs.forEach(dialog => {
            const row = dialogRowTemplate.content.cloneNode(true);
            const item = row.querySelector('.dialog-item');

            item.dataset.dialogId = dialog.id;
            item.dataset.dialogStatus = dialog.status;
            item.dataset.userId = dialog.user_id;

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

    // === Обновление состояния кнопки отправки ===
    function updateSendButtonState() {
        if (!sendChatMessageBtn) return;

        const isClosed = currentDialogStatus === 'closed';
        sendChatMessageBtn.disabled = isClosed;

        // Обновляем текст кнопки с учётом гостя И статуса
        if (isClosed) {
            sendChatMessageBtn.textContent = 'Закрыт';
        } else {
            sendChatMessageBtn.textContent = isGuestDialog ? 'Отправить на email' : 'Отправить';
        }
    }

    // Открытие модального окна
    async function openChatModal(dialogId) {
        currentDialogId = dialogId;

        const dialogRow = document.querySelector(`.dialog-item[data-dialog-id="${dialogId}"]`);
        if (!dialogRow) {
            console.error('Диалог не найден в DOM:', dialogId);
            return;
        }

        currentDialogStatus = dialogRow.dataset.dialogStatus;
        isGuestDialog = dialogRow.dataset.userId === 'null';

        // Обновляем UI модального окна
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

            updateSendButtonState();

        } catch (error) {
            console.error(`Ошибка загрузки сообщений диалога ${dialogId}:`, error);
            chatMessagesContainer.innerHTML = '<div style="color:red; padding:10px;">Не удалось загрузить сообщения.</div>';
            updateSendButtonState();
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

    // Отправка нового сообщения — с защитой от закрытых диалогов
    async function sendNewMessage() {
        if (currentDialogStatus === 'closed') {
            showMessage('Нельзя отправлять сообщения в закрытый диалог.', 'warning');
            return;
        }

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

            // Перезагружаем сообщения
            const res = await fetch(`/api/chat/dialogs/${currentDialogId}/messages`);
            const messages = await res.json();
            renderMessages(messages);

        } catch (error) {
            console.error('Ошибка отправки сообщения:', error);
            showMessage(`Ошибка: ${error.message || 'неизвестная'}`, 'error');
        } finally {
            sendBtn.textContent = originalText;
            setTimeout(updateSendButtonState, 0);
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
            currentDialogStatus = null;
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