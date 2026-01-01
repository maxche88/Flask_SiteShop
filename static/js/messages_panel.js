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
    const saveTopicsBtn = document.getElementById('save-topics-btn');

    // === Глобальный делегированный обработчик для редактирования ячеек ===
    topicsTableBody.addEventListener('click', function (e) {
        if (e.target.classList.contains('editable') && !e.target.querySelector('input')) {
            startEditing(e);
        }
    });

    // Отслеживаем изменения для активации кнопки "Сохранить все"
    let hasUnsavedChanges = false;
    function markUnsaved() {
        hasUnsavedChanges = true;
        if (saveTopicsBtn) saveTopicsBtn.disabled = false;
    }

    let editingCell = null;
    let currentDialogId = null;
    let currentDialogStatus = null;
    let isGuestDialog = false;

    // ... (весь остальной код без изменений до topicsModal) ...

    // Открытие модалки тем
    document.getElementById('mess-topics-btn').addEventListener('click', async () => {
        topicsModal.classList.remove('hidden');
        hasUnsavedChanges = false;
        if (saveTopicsBtn) saveTopicsBtn.disabled = true;
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

    // Загрузка тем (только для админки!)
    async function loadTopics() {
        try {
            const response = await fetch('/api/chat/admin/topics', {
                method: 'GET',
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Не удалось загрузить темы');
            const topics = await response.json();
            renderTopics(topics);
        } catch (err) {
            console.error('Ошибка загрузки тем:', err);
            topicsTableBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:red;">Ошибка загрузки</td></tr>';
        }
    }

    // Отображение тем
    function renderTopics(topics) {
        topicsTableBody.innerHTML = '';
        if (topics.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="5" style="text-align:center;color:#777;">Нет тем</td>`;
            topicsTableBody.appendChild(row);
            return;
        }

        topics.forEach(topic => {
            const row = document.createElement('tr');
            row.dataset.topicId = topic.id;
            row.dataset.originalName = topic.name;
            row.dataset.originalDescription = topic.description || '';
            row.dataset.originalActive = topic.is_active;

            // Чекбокс: checked, если is_active === true
            const isActiveHtml = `
            <input type="checkbox" ${topic.is_active ? 'checked' : ''} data-field="is_active">
        `;

            const deleteBtnHtml = `
            <button class="btn-delete-topic" data-topic-id="${topic.id}" title="Удалить тему">×</button>
        `;

            row.innerHTML = `
            <td>${topic.id}</td>
            <td class="editable" data-field="name">${escapeHtml(topic.name)}</td>
            <td class="editable" data-field="description">${escapeHtml(topic.description || '')}</td>
            <td>${isActiveHtml}</td>
            <td>${deleteBtnHtml}</td>
        `;
            topicsTableBody.appendChild(row);
        });

        // Обработчики чекбоксов и редактируемых ячеек для отслеживания изменений
        topicsTableBody.querySelectorAll('.editable, input[type="checkbox"][data-field="is_active"]').forEach(el => {
            const type = el.classList.contains('editable') ? 'cell' : 'checkbox';
            if (type === 'cell') {
                // Уже есть делегирование, но добавим метку изменения
                // (обработка будет в startEditing -> save)
            } else {
                el.addEventListener('change', markUnsaved);
            }
        });
    }

    // Начало inline-редактирования
    function startEditing(e) {
        if (editingCell) return;

        const cell = e.target;
        const field = cell.dataset.field;
        const currentValue = cell.textContent;

        editingCell = cell;

        const input = document.createElement('input');
        input.type = 'text';
        input.value = currentValue;
        input.className = 'inline-edit-input';
        input.style.width = '100%';
        input.style.padding = '4px';
        input.style.border = '1px solid #ccc';
        input.style.borderRadius = '3px';

        cell.innerHTML = '';
        cell.appendChild(input);
        input.focus();

        const revert = () => {
            cell.textContent = escapeHtml(currentValue);
            editingCell = null;
        };

        const saveEdit = () => {
            const newValue = input.value.trim();
            if (newValue !== currentValue) {
                cell.textContent = escapeHtml(newValue || '');
                markUnsaved();
            } else {
                cell.textContent = escapeHtml(currentValue);
            }
            editingCell = null;
        };

        input.addEventListener('blur', saveEdit);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveEdit();
            } else if (e.key === 'Escape') {
                revert();
            }
        });
    }

    // Добавление новой темы
    addTopicBtn.addEventListener('click', () => {
        const newRow = document.createElement('tr');
        newRow.dataset.topicId = 'new';
        newRow.dataset.isNew = 'true';

        newRow.innerHTML = `
        <td>—</td>
        <td class="editable" data-field="name">&nbsp;</td>
        <td class="editable" data-field="description">&nbsp;</td>
        <td><input type="checkbox" checked data-field="is_active"></td>
        <td><button class="btn-delete-topic" data-topic-id="new" title="Удалить тему">×</button></td>
    `;

        topicsTableBody.appendChild(newRow);
        markUnsaved();

        // Активируем редактирование в поле "Название"
        const nameCell = newRow.querySelector('[data-field="name"]');
        const clickEvent = new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window
        });
        nameCell.dispatchEvent(clickEvent);
    });

    // Сохранение всех изменений
    async function saveAllTopics() {
        const rows = topicsTableBody.querySelectorAll('tr[data-topic-id]');
        const createPromises = [];
        const updatePromises = [];

        for (const row of rows) {
            const topicId = row.dataset.topicId;
            const name = row.querySelector('[data-field="name"]').textContent.trim();
            const description = row.querySelector('[data-field="description"]').textContent.trim();
            const isActive = row.querySelector('input[type="checkbox"]').checked;

            if (!name) {
                showMessage('Название темы обязательно', 'error');
                return;
            }

            if (topicId === 'new') {
                // Создание
                const promise = fetch('/api/chat/topics', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ name, description, is_active: isActive })
                }).then(async res => {
                    if (!res.ok) {
                        const err = await res.json().catch(() => ({}));
                        throw new Error(err.error || 'Не удалось создать тему');
                    }
                    const saved = await res.json();
                    row.dataset.topicId = saved.id;
                    row.querySelector('td:first-child').textContent = saved.id;
                    return { action: 'created', id: saved.id };
                });
                createPromises.push(promise);
            } else {
                // Проверка на изменения
                const originalName = row.dataset.originalName;
                const originalDesc = row.dataset.originalDescription;
                const originalActive = row.dataset.originalActive === 'true';

                if (name !== originalName || description !== originalDesc || isActive !== originalActive) {
                    const promise = fetch(`/api/chat/topics/${topicId}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'same-origin',
                        body: JSON.stringify({ name, description, is_active: isActive })
                    }).then(async res => {
                        if (!res.ok) {
                            const err = await res.json().catch(() => ({}));
                            throw new Error(err.error || 'Не удалось обновить тему');
                        }
                        // Обновляем оригинальные значения после сохранения
                        row.dataset.originalName = name;
                        row.dataset.originalDescription = description;
                        row.dataset.originalActive = isActive;
                        return { action: 'updated', id: topicId };
                    });
                    updatePromises.push(promise);
                }
            }
        }

        if (createPromises.length === 0 && updatePromises.length === 0) {
            showMessage('Нет изменений для сохранения', 'info');
            return;
        }

        try {
            await Promise.all([...createPromises, ...updatePromises]);
            hasUnsavedChanges = false;
            if (saveTopicsBtn) saveTopicsBtn.disabled = true;
            showMessage('Все изменения сохранены', 'success');
        } catch (err) {
            console.error('Ошибка при сохранении тем:', err);
            showMessage(`Ошибка: ${err.message}`, 'error');
        }
    }

    // Кнопка "Сохранить все"
    if (saveTopicsBtn) {
        saveTopicsBtn.addEventListener('click', saveAllTopics);
    }

    // Удаление темы (делегирование)
    topicsTableBody.addEventListener('click', async (e) => {
        if (!e.target.classList.contains('btn-delete-topic')) return;

        const topicId = e.target.dataset.topicId;
        const row = e.target.closest('tr');

        // Удаление черновика (новой строки)
        if (topicId === 'new') {
            row.remove();
            if (topicsTableBody.children.length === 0) {
                const emptyRow = document.createElement('tr');
                emptyRow.innerHTML = `<td colspan="5" style="text-align:center;color:#777;">Нет тем</td>`;
                topicsTableBody.appendChild(emptyRow);
            }
            markUnsaved(); // состояние изменилось
            return;
        }

        // Подтверждение удаления существующей темы
        const topicName = row.querySelector('[data-field="name"]')?.textContent.trim() || 'без названия';
        if (!confirm(`Вы уверены, что хотите удалить тему "${topicName}"?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/chat/topics/${topicId}`, {
                method: 'DELETE',
                credentials: 'same-origin'
            });
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.error || 'Не удалось удалить тему');
            }

            row.remove();
            markUnsaved();
            showMessage('Тема удалена', 'success');

            if (topicsTableBody.children.length === 0) {
                const emptyRow = document.createElement('tr');
                emptyRow.innerHTML = `<td colspan="5" style="text-align:center;color:#777;">Нет тем</td>`;
                topicsTableBody.appendChild(emptyRow);
            }
        } catch (error) {
            console.error('Ошибка удаления темы:', error);
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

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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