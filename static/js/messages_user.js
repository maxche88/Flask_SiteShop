document.addEventListener('DOMContentLoaded', function () {
    // DOM
    const dialogsList = document.getElementById('dialogs-list');
    const chatModal = document.getElementById('chat-modal');
    const chatMessagesContainer = document.getElementById('chat-messages-container');
    const modalDialogId = document.getElementById('modal-dialog-id');
    const closeChatModalBtn = document.getElementById('close-chat-modal');
    const chatMessageInput = document.getElementById('chat-message-input');
    const sendChatMessageBtn = document.getElementById('send-chat-message');
    const infoPanel = document.getElementById('messages-info-panel');

    // Создание диалога
    const openCreateBtn = document.getElementById('open-create-dialog-modal');
    const createDialogModal = document.getElementById('create-dialog-modal');
    const closeCreateBtn = document.getElementById('close-create-dialog-modal');
    const createForm = document.getElementById('create-dialog-form');
    const topicSelect = document.getElementById('dialog-topic');

    let currentDialogId = null;

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

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // === Загрузка диалогов ===
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
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="5" style="text-align:center; padding:20px; color:#777;">
                    У вас пока нет сообщений
                </td>
            `;
            dialogsList.appendChild(row);
            return;
        }

        dialogs.forEach(dialog => {
            const row = document.createElement('tr');
            row.className = 'dialog-row';
            if (dialog.unread_count > 0) {
                row.classList.add('has-unread'); // ← подсветка
            }
            row.dataset.dialogId = dialog.id;

            // Определяем собеседника
            const partnerLabel = dialog.last_sender_role === 'suser' ? 'Менеджер' :
                                (dialog.last_sender_role === 'admin' ? 'Администратор' : 'Поддержка');

            // Иконка закрытия (можно заменить на SVG или другую иконку)
            const closeIcon = `
                <button class="dialog-close-btn" title="Закрыть диалог">
                    ✕
                </button>
            `;

            row.innerHTML = `
                <td class="dialog-actions">${closeIcon}</td>
                <td>${escapeHtml(dialog.topic_name)}</td>
                <td>${partnerLabel}</td>
                <td class="last-message-preview">${escapeHtml(dialog.last_message_preview?.substring(0, 50) || '—')}</td>
                <td>${formatDate(dialog.updated_at)}</td>
            `;

            // Обработчик клика по строке — открыть чат
            row.addEventListener('click', (e) => {
                // Игнорируем клик по кнопке закрытия
                if (e.target.closest('.dialog-close-btn')) return;
                openChatModal(dialog.id);
            });

            // Обработчик клика по кнопке закрытия
            const closeBtn = row.querySelector('.dialog-close-btn');
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // не открывать чат
                confirmCloseDialog(dialog.id);
            });

            dialogsList.appendChild(row);
        });
    }

    async function confirmCloseDialog(dialogId) {
        if (!confirm('Вы уверены, что хотите закрыть этот диалог?')) {
            return;
        }

        try {
            const response = await fetch(`/api/chat/dialogs/${dialogId}/close`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.error || `HTTP ${response.status}`);
            }

            loadDialogs(); 

        } catch (error) {
            console.error('Ошибка при закрытии диалога:', error);
            showMessage(`Не удалось закрыть диалог: ${error.message}`, 'error');
        }
    }

    // === Открытие чата ===
    async function openChatModal(dialogId) {
        currentDialogId = dialogId;
        modalDialogId.textContent = dialogId;
        chatMessagesContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#777;">Загрузка...</div>';
        chatModal.classList.remove('hidden');
        if (chatMessageInput) {
            chatMessageInput.value = '';
            chatMessageInput.focus();
        }

        try {
            const response = await fetch(`/api/chat/user-dialogs/${dialogId}/messages`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const messages = await response.json();
            renderMessages(messages);
        } catch (error) {
            console.error(`Ошибка загрузки сообщений диалога ${dialogId}:`, error);
            chatMessagesContainer.innerHTML = '<div style="color:red; padding:15px; text-align:center;">Не удалось загрузить сообщения.</div>';
        }
    }

    function renderMessages(messages) {
        chatMessagesContainer.innerHTML = '';

        if (!messages || messages.length === 0) {
            chatMessagesContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#777;">Нет сообщений</div>';
            return;
        }

        messages.forEach(msg => {
            const isSent = msg.sender_role === 'user';
            const senderLabel = isSent ? 'Вы' : 
                (msg.sender_role === 'suser' ? 'Менеджер' : 
                (msg.sender_role === 'admin' ? 'Администратор' : 'Поддержка'));

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

    // === Отправка сообщения ===
    async function sendNewMessage() {
        const text = chatMessageInput?.value.trim();
        if (!text) {
            showMessage('Сообщение не может быть пустым.', 'warning');
            return;
        }

        if (!currentDialogId) {
            showMessage('Ошибка: диалог не выбран.', 'error');
            return;
        }

        const btn = sendChatMessageBtn;
        const originalText = btn?.textContent;
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Отправка...';
        }

        try {
            const response = await fetch(`/api/chat/user-dialogs/${currentDialogId}/reply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ text: text })
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.error || `HTTP ${response.status}`);
            }

            chatMessageInput.value = '';
            const res = await fetch(`/api/chat/user-dialogs/${currentDialogId}/messages`);
            const messages = await res.json();
            renderMessages(messages);

        } catch (error) {
            console.error('Ошибка отправки:', error);
            showMessage(`Ошибка: ${error.message || 'неизвестная'}`, 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = originalText || 'Отправить';
            }
        }
    }

    // === Закрытие чата ===
    function closeChatModal() {
        chatModal.classList.add('hidden');
        currentDialogId = null;
    }

    if (closeChatModalBtn) closeChatModalBtn.addEventListener('click', closeChatModal);
    const overlay = chatModal?.querySelector('.chat-modal-overlay');
    if (overlay) overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeChatModal();
    });

    if (chatMessageInput) {
        chatMessageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendNewMessage();
            }
        });
    }
    if (sendChatMessageBtn) sendChatMessageBtn.addEventListener('click', sendNewMessage);

    // === Создание диалога ===
    async function loadTopics() {
        try {
            const response = await fetch('/api/chat/topics', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });
            if (!response.ok) throw new Error('Не удалось загрузить категории.');

            const topics = await response.json();
            topicSelect.innerHTML = '<option value="">— Выберите категорию —</option>';
            topics.forEach(topic => {
                const option = document.createElement('option');
                option.value = topic.id;
                option.textContent = topic.name;
                topicSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Ошибка загрузки тем:', error);
            topicSelect.innerHTML = '<option value="">Ошибка загрузки</option>';
        }
    }

    function openCreateDialogModal() {
        loadTopics();
        createDialogModal.classList.remove('hidden');
    }

    function closeCreateDialogModal() {
        createDialogModal.classList.add('hidden');
        if (createForm) createForm.reset();
    }

    async function handleCreateDialogSubmit(e) {
        e.preventDefault();
        const formData = new FormData(createForm);
        let topicId = formData.get('topic_id');
        const text = formData.get('text').trim();

        if (!text) {
            alert('Сообщение не может быть пустым.');
            return;
        }
        if (!topicId || topicId === "" || isNaN(topicId)) {
            alert('Пожалуйста, выберите категорию.');
            return;
        }

        const data = {
            text: text,
            topic_id: parseInt(topicId, 10)
        };

        const submitBtn = createForm.querySelector('.btn-submit');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Отправка...';

        try {
            const response = await fetch('/api/chat/dialogs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!response.ok) {
                const errorMsg = result.errors?.join('\n') || result.error || 'Неизвестная ошибка';
                alert(`Ошибка: ${errorMsg}`);
                return;
            }

            alert('Ваше сообщение отправлено!');
            closeCreateDialogModal();
            loadDialogs();

        } catch (error) {
            console.error('Ошибка при создании диалога:', error);
            alert('Не удалось отправить сообщение. Попробуйте позже.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    }

    // Подключение обработчиков создания диалога
    if (openCreateBtn) openCreateBtn.addEventListener('click', openCreateDialogModal);
    if (closeCreateBtn) closeCreateBtn.addEventListener('click', closeCreateDialogModal);
    if (createDialogModal) {
        const modalOverlay = createDialogModal.querySelector('.dialog-modal-overlay');
        if (modalOverlay) {
            modalOverlay.addEventListener('click', (e) => {
                if (e.target === createDialogModal) closeCreateDialogModal();
            });
        }
    }
    if (createForm) createForm.addEventListener('submit', handleCreateDialogSubmit);

    // === Запуск ===
    loadDialogs();
});