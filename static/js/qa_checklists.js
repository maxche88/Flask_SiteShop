document.addEventListener('DOMContentLoaded', () => {
    // =================================================
    // 🔧 ИНИЦИАЛИЗАЦИЯ ЭЛЕМЕНТОВ
    // =================================================
    const tableContainer = document.getElementById('checklistsTableContainer');
    const messageDiv = document.getElementById('checklistsMessage');
    const openCreateBtn = document.getElementById('openCreateChecklistModalBtn');
    const createModal = document.getElementById('checklistModalBackdrop');
    const viewModal = document.getElementById('viewChecklistModalBackdrop');
    const checklistForm = document.getElementById('checklistForm');
    const checklistTitle = document.getElementById('checklistTitle');
    const itemsContainer = document.getElementById('checklistItemsContainer');
    const addItemBtn = document.getElementById('addChecklistItemBtn');
    const cancelBtn = document.getElementById('cancelChecklistBtn');
    const closeViewBtn = document.getElementById('closeViewChecklistModalBtn');
    const btnEditInModal = document.getElementById('btnEditChecklistInModal');
    const selectAll = document.getElementById('selectAllChecklists');

    let currentChecklistId = null;
    let currentChecklistData = null;

    // =================================================
    // ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    // =================================================
    function showMessage(text, isError = false) {
        if (!messageDiv) return;
        messageDiv.textContent = text;
        messageDiv.className = isError ? 'checklist-message error' : 'checklist-message info';
        messageDiv.style.display = 'block';
        if (!isError) {
            setTimeout(() => {
                if (messageDiv) messageDiv.style.display = 'none';
            }, 5000);
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatDateTime(isoString) {
        if (!isoString) return '—';
        return new Date(isoString).toLocaleString('ru-RU', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function handleSelectAll() {
        if (!selectAll || !tableContainer) return;
        const checkboxes = tableContainer.querySelectorAll('.checklist-checkbox');
        checkboxes.forEach(cb => cb.checked = selectAll.checked);
    }

    // =================================================
    // ЗАГРУЗКА И ОТОБРАЖЕНИЕ СПИСКА ЧЕК-ЛИСТОВ
    // =================================================
    async function loadChecklists() {
        try {
            const res = await fetch('/api/checklists');
            if (!res.ok) throw new Error('Не удалось загрузить чек-листы');
            const checklists = await res.json();
            renderChecklists(checklists);
        } catch (err) {
            console.error('Ошибка загрузки чек-листов:', err);
            showMessage('Не удалось загрузить чек-листы', true);
        }
    }

    function renderChecklists(checklists) {
        const existingRows = tableContainer.querySelectorAll('.checklist-row');
        existingRows.forEach(row => row.remove());

        const template = document.getElementById('checklist-row-template');
        checklists.forEach(cl => {
            const row = template.content.cloneNode(true).querySelector('.checklist-row');
            row.querySelector('.checklist-checkbox').dataset.id = cl.id;
            row.querySelector('.id-cell').textContent = cl.id;
            row.querySelector('.title-cell').textContent = escapeHtml(cl.title);
            row.querySelector('.author-id-cell').textContent = cl.author_id || '—';
            row.querySelector('.total-items-cell').textContent = cl.total_items || 0;
            row.querySelector('.completed-items-cell').textContent = cl.completed_items || 0;
            row.querySelector('.created-at-cell').textContent = formatDateTime(cl.created_at);
            tableContainer.appendChild(row);
        });

        if (selectAll) {
            selectAll.checked = false;
            selectAll.removeEventListener('change', handleSelectAll);
            selectAll.addEventListener('change', handleSelectAll);
        }
    }

    // =================================================
    // РЕЖИМ ВЫПОЛНЕНИЯ ЧЕК-ЛИСТА
    // =================================================
    async function openViewChecklist(id) {
        try {
            const res = await fetch(`/api/checklists/${id}`);
            if (!res.ok) throw new Error('Чек-лист не найден');
            const checklist = await res.json();
            currentChecklistId = id;
            currentChecklistData = checklist;
            renderExecutionView(checklist);
            viewModal.classList.add('is-open');
        } catch (err) {
            console.error(err);
            showNotification(err.message || 'Ошибка загрузки чек-листа');
        }
    }

    function renderExecutionView(checklist) {
        document.getElementById('viewChecklistId').textContent = checklist.id;
        document.getElementById('viewChecklistTitle').textContent = checklist.title;
        const content = document.getElementById('viewChecklistContent');
        content.innerHTML = '';

        if (checklist.items.length === 0) {
            content.innerHTML = '<em>Нет пунктов</em>';
            return;
        }

        const template = document.getElementById('checklist-item-execution-template');

        checklist.items.forEach((item, index) => {
            const row = template.content.cloneNode(true).querySelector('.checklist-item-execution');
            row.dataset.itemIndex = index;
            
            const commentInput = row.querySelector('.comment-input');
            if (commentInput) {
                commentInput.id = `comment-input-${currentChecklistId}-${index}`;
                commentInput.name = `comment_${index}`;
            }


            // Отображаем номер пункта (из данных)
            row.querySelector('.item-number').textContent = item.id_item || (index + 1);

            // Отображаем название действия
            row.querySelector('.checklist-item-text').textContent = escapeHtml(item.action_name);

            // Отображаем название действия с tooltip
            const textEl = row.querySelector('.checklist-item-text');
            textEl.textContent = escapeHtml(item.action_name);
            textEl.title = item.comment || 'Комментарий отсутствует';

            // Статус
            const statusBtns = row.querySelectorAll('.status-btn');
            const currentResult = item.result || 'skipped';
            statusBtns.forEach(btn => {
                const btnStatus = btn.classList[1];
                if (currentResult === btnStatus) {
                    btn.classList.add('active');
                }
            });

            // Комментарий
            const commentToggle = row.querySelector('.comment-toggle-btn');

            // Обновляем состояние иконки
            if (item.comment) {
                commentToggle.classList.add('has-comment');
                commentToggle.title = 'Редактировать комментарий';
            } else {
                commentToggle.classList.remove('has-comment');
                commentToggle.title = 'Добавить комментарий';
            }

            commentInput.value = item.comment || '';

            // Обработчики статусов
            statusBtns.forEach(btn => {
                btn.addEventListener('click', async () => {
                    const newStatus = btn.classList[1];
                    await updateChecklistItem(index, { result: newStatus });

                    // Обновляем UI
                    statusBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');

                    // Обновляем кэш
                    currentChecklistData.items[index].result = newStatus;
                    loadChecklists();
                });
            });

            // Комментарий: переключение
            commentToggle.addEventListener('click', () => {
                const commentSection = row.querySelector('.comment-section');
                const isOpen = commentSection.style.display === 'block';
                commentSection.style.display = isOpen ? 'none' : 'block';
                if (!isOpen) commentInput.focus();
            });

            // Комментарий: отмена
            row.querySelector('.comment-cancel').addEventListener('click', () => {
                row.querySelector('.comment-section').style.display = 'none';
            });

            // Комментарий: сохранение
            row.querySelector('.comment-save').addEventListener('click', async () => {
                const newComment = commentInput.value.trim();
                await updateChecklistItem(index, { comment: newComment });

                // Обновляем UI
                if (newComment) {
                    commentToggle.classList.add('has-comment');
                } else {
                    commentToggle.classList.remove('has-comment');
}

                // Обновляем кэш
                currentChecklistData.items[index].comment = newComment;
                row.querySelector('.comment-section').style.display = 'none';
                loadChecklists();
            });

            content.appendChild(row);
        });
    }

    // =================================================
    // ЧАСТИЧНОЕ ОБНОВЛЕНИЕ ПУНКТА (ПО ИНДЕКСУ)
    // =================================================
    async function updateChecklistItem(itemIndex, updateData) {
        try {
            const res = await fetch(`/api/checklists/${currentChecklistId}/items/${itemIndex}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData)
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.error || 'Неизвестная ошибка');
            }

            // Обновляем локальный кэш
            if (currentChecklistData?.items[itemIndex]) {
                Object.assign(currentChecklistData.items[itemIndex], updateData);
            }
        } catch (err) {
            console.error('Ошибка сохранения пункта:', err);
            showNotification('Не удалось сохранить изменения. Проверьте соединение.');
        }
    }

    // =================================================
    // СОЗДАНИЕ / РЕДАКТИРОВАНИЕ ЧЕК-ЛИСТА
    // =================================================
    if (openCreateBtn && createModal) {
        openCreateBtn.addEventListener('click', () => {
            currentChecklistId = null;
            currentChecklistData = null;
            document.getElementById('checklistModalTitle').textContent = 'Новый чек-лист';
            checklistForm.reset();
            if (itemsContainer) itemsContainer.innerHTML = '';
            createModal.classList.add('is-open');
        });
    }

    if (cancelBtn && createModal) {
        cancelBtn.addEventListener('click', () => createModal.classList.remove('is-open'));
    }

    if (btnEditInModal && createModal && viewModal) {
        btnEditInModal.addEventListener('click', () => {
            viewModal.classList.remove('is-open');
            createModal.classList.add('is-open');
            loadChecklistForEdit(currentChecklistId);
        });
    }

    if (addItemBtn) {
        addItemBtn.addEventListener('click', () => addItemRow());
    }

    function addItemRow(text = '') {
        const template = document.getElementById('checklist-item-template');
        const row = template.content.cloneNode(true).querySelector('.checklist-item-row');
        const input = row.querySelector('.item-text-input');
        const removeBtn = row.querySelector('.remove-item-btn');

        input.value = text;

        // Удаление — только из DOM
        removeBtn.addEventListener('click', () => row.remove());

        if (itemsContainer) itemsContainer.appendChild(row);
    }

    async function loadChecklistForEdit(id) {
        try {
            const res = await fetch(`/api/checklists/${id}`);
            if (!res.ok) throw new Error('Не удалось загрузить для редактирования');
            const cl = await res.json();
            checklistTitle.value = cl.title;
            if (itemsContainer) itemsContainer.innerHTML = '';
            // Загружаем только текст пунктов
            cl.items.forEach(item => addItemRow(item.action_name));
            document.getElementById('checklistModalTitle').textContent = `Редактировать чек-лист #${id}`;
            currentChecklistId = id;
        } catch (err) {
            showNotification('Ошибка при загрузке для редактирования');
            console.error(err);
        }
    }

    if (checklistForm) {
        checklistForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const title = checklistTitle.value.trim();
            if (!title) {
                showNotification('Укажите название чек-листа');
                return;
            }

            const items = [];
            const rows = itemsContainer.querySelectorAll('.checklist-item-row');
            rows.forEach(row => {
                const text = row.querySelector('.item-text-input').value.trim();
                if (text) {
                    items.push({ action_name: text });
                }
            });

            if (items.length === 0) {
                showNotification('Добавьте хотя бы один пункт');
                return;
            }

            const payload = { title, items };
            let endpoint = '/api/checklists';
            let method = 'POST';

            if (currentChecklistId) {
                endpoint += `/${currentChecklistId}`;
                method = 'PATCH';
            }

            try {
                const res = await fetch(endpoint, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    showNotification(currentChecklistId ? 'Чек-лист обновлён!' : 'Чек-лист создан!');
                    createModal.classList.remove('is-open');
                    loadChecklists();
                } else {
                    const data = await res.json();
                    showNotification('Ошибка: ' + (data.error || 'неизвестная'));
                }
            } catch (err) {
                showNotification('Ошибка сети');
                console.error(err);
            }
        });
    }

    // =================================================
    // ЗАКРЫТИЕ МОДАЛКИ И КНОПКИ "ОТМЕТИТЬ ВСЁ"
    // =================================================
    if (closeViewBtn && viewModal) {
        closeViewBtn.addEventListener('click', () => {
            viewModal.classList.remove('is-open');
        });
    }

    // Кнопка "Отметить всё" в хедере модалки
    const headerMarkAllDoneBtn = document.getElementById('headerMarkAllDoneBtn');
    if (headerMarkAllDoneBtn) {
        headerMarkAllDoneBtn.addEventListener('click', async () => {
            if (!currentChecklistId) return;
            if (!confirm('Отметить все пункты как выполненные?')) return;
            await markAllItemsAsDone();
        });
    }

    async function markAllItemsAsDone() {
        try {
            const res = await fetch(`/api/checklists/${currentChecklistId}/mark-all-done`, {
                method: 'PATCH'
            });
            if (res.ok) {
                await openViewChecklist(currentChecklistId);
                loadChecklists();
            } else {
                const data = await res.json();
                showNotification('Ошибка: ' + (data.error || 'не удалось обновить'));
            }
        } catch (err) {
            showNotification('Ошибка сети');
            console.error(err);
        }
    }

    // Открытие чек-листа по клику на название
    if (tableContainer) {
        tableContainer.addEventListener('click', (e) => {
            const titleCell = e.target.closest('.title-cell');
            if (!titleCell) return;
            const row = titleCell.closest('.checklist-row');
            const id = row.querySelector('.checklist-checkbox').dataset.id;
            openViewChecklist(Number(id));
        });
    }

    // =================================================
    // УДАЛЕНИЕ ЧЕК-ЛИСТОВ
    // =================================================
    const btnDeleteSelected = document.getElementById('openDeleteChecklistBtn');

    function updateDeleteButton() {
        if (!btnDeleteSelected || !tableContainer) return;
        const checked = tableContainer.querySelectorAll('.checklist-checkbox:checked');
        btnDeleteSelected.disabled = checked.length === 0;
    }

    if (tableContainer) {
        tableContainer.addEventListener('change', updateDeleteButton);
    }
    if (selectAll) {
        selectAll.addEventListener('change', updateDeleteButton);
    }

    if (btnDeleteSelected) {
        btnDeleteSelected.addEventListener('click', async () => {
            const checked = tableContainer.querySelectorAll('.checklist-checkbox:checked');
            const ids = Array.from(checked).map(cb => cb.dataset.id);

            if (ids.length === 0) {
                showMessage('Не выбрано ни одного чек-листа', true);
                return;
            }

            if (!confirm(`Удалить ${ids.length} чек-лист(а/ов)? Это действие нельзя отменить.`)) {
                return;
            }

            try {
                const results = await Promise.allSettled(
                    ids.map(id =>
                        fetch(`/api/checklists/${id}`, { method: 'DELETE' })
                    )
                );

                const succeeded = results.filter(r => r.status === 'fulfilled' && r.value.ok).length;
                const failed = ids.length - succeeded;

                if (succeeded > 0) {
                    showMessage(`Удалено чек-листов: ${succeeded}`, false);
                    if (failed > 0) {
                        console.warn(`${failed} чек-листов не удалось удалить`);
                    }
                    loadChecklists();
                } else {
                    showMessage('Не удалось удалить ни одного чек-листа', true);
                }
            } catch (err) {
                console.error('Ошибка при удалении чек-листов:', err);
                showMessage('Ошибка сети', true);
            }
        });
    }

    loadChecklists();
});