document.addEventListener('DOMContentLoaded', () => {
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
    const clearFormBtn = document.getElementById('clearChecklistFormBtn');
    const closeViewBtn = document.getElementById('closeViewChecklistModalBtn');
    const btnEditInModal = document.getElementById('btnEditChecklistInModal');
    const btnMarkAllDone = document.getElementById('btnMarkAllDone');
    const selectAll = document.getElementById('selectAllChecklists');

    let currentChecklistId = null;

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

    async function openViewChecklist(id) {
        try {
            currentChecklistId = id;
            const res = await fetch(`/api/checklists/${id}`);
            if (!res.ok) throw new Error('Чек-лист не найден');
            const checklist = await res.json();
            renderViewChecklist(checklist);
            viewModal.classList.add('is-open');
        } catch (err) {
            console.error(err);
            alert(err.message || 'Ошибка загрузки чек-листа');
        }
    }

    function renderViewChecklist(checklist) {
        document.getElementById('viewChecklistId').textContent = checklist.id;
        const content = document.getElementById('viewChecklistContent');
        content.innerHTML = '';

        checklist.items.forEach(item => {
            const div = document.createElement('div');
            div.className = `checklist-item-view ${item.is_done ? 'completed' : ''}`;
            div.innerHTML = `
                <input type="checkbox" class="checklist-item-checkbox" ${item.is_done ? 'checked' : ''} disabled>
                <span class="checklist-item-text">${escapeHtml(item.text)}</span>
            `;
            content.appendChild(div);
        });

        if (checklist.items.length === 0) {
            content.innerHTML = '<em>Нет пунктов</em>';
        }
    }

    if (openCreateBtn && createModal) {
        openCreateBtn.addEventListener('click', () => {
            currentChecklistId = null;
            document.getElementById('checklistModalTitle').textContent = 'Новый чек-лист';
            checklistForm.reset();
            if (itemsContainer) itemsContainer.innerHTML = '';
            createModal.classList.add('is-open');
        });
    }

    if (cancelBtn && createModal) {
        cancelBtn.addEventListener('click', () => createModal.classList.remove('is-open'));
    }

    if (closeViewBtn && viewModal) {
        closeViewBtn.addEventListener('click', () => viewModal.classList.remove('is-open'));
    }

    if (btnEditInModal && createModal && viewModal) {
        btnEditInModal.addEventListener('click', () => {
            viewModal.classList.remove('is-open');
            createModal.classList.add('is-open');
            loadChecklistForEdit(currentChecklistId);
        });
    }

    async function loadChecklistForEdit(id) {
        try {
            const res = await fetch(`/api/checklists/${id}`);
            if (!res.ok) throw new Error('Не удалось загрузить для редактирования');
            const cl = await res.json();
            checklistTitle.value = cl.title;
            if (itemsContainer) itemsContainer.innerHTML = '';
            cl.items.forEach(item => addItemRow(item.text, item.is_done));
            document.getElementById('checklistModalTitle').textContent = `Редактировать чек-лист #${id}`;
            currentChecklistId = id;
        } catch (err) {
            alert('Ошибка при загрузке для редактирования');
            console.error(err);
        }
    }

    if (addItemBtn) {
        addItemBtn.addEventListener('click', () => addItemRow());
    }

    function addItemRow(text = '', isDone = false) {
        const template = document.getElementById('checklist-item-template');
        const row = template.content.cloneNode(true).querySelector('.checklist-item-row');
        const input = row.querySelector('.item-text-input');
        const checkbox = row.querySelector('.item-done-checkbox');
        const removeBtn = row.querySelector('.remove-item-btn');

        input.value = text;
        checkbox.checked = isDone;
        checkbox.disabled = false;

        removeBtn.addEventListener('click', () => row.remove());

        if (itemsContainer) itemsContainer.appendChild(row);
    }

    if (checklistForm) {
        checklistForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const title = checklistTitle.value.trim();
            if (!title) {
                alert('Укажите название чек-листа');
                return;
            }

            const items = [];
            const rows = itemsContainer.querySelectorAll('.checklist-item-row');
            rows.forEach(row => {
                const text = row.querySelector('.item-text-input').value.trim();
                const done = row.querySelector('.item-done-checkbox').checked;
                if (text) items.push({ text, is_done: done });
            });

            if (items.length === 0) {
                alert('Добавьте хотя бы один пункт');
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
                    alert(currentChecklistId ? 'Чек-лист обновлён!' : 'Чек-лист создан!');
                    createModal.classList.remove('is-open');
                    loadChecklists();
                } else {
                    const data = await res.json();
                    alert('Ошибка: ' + (data.error || 'неизвестная'));
                }
            } catch (err) {
                alert('Ошибка сети');
                console.error(err);
            }
        });
    }

    if (clearFormBtn && itemsContainer) {
        clearFormBtn.addEventListener('click', () => {
            checklistForm.reset();
            itemsContainer.innerHTML = '';
        });
    }

    if (btnMarkAllDone) {
        btnMarkAllDone.addEventListener('click', async () => {
            if (!currentChecklistId) return;
            if (!confirm('Отметить все пункты как выполненные?')) return;
            try {
                const res = await fetch(`/api/checklists/${currentChecklistId}/mark-all-done`, {
                    method: 'PATCH'
                });
                if (res.ok) {
                    alert('Все пункты отмечены как выполненные');
                    await openViewChecklist(currentChecklistId);
                    loadChecklists();
                } else {
                    alert('Не удалось обновить');
                }
            } catch (err) {
                alert('Ошибка сети');
                console.error(err);
            }
        });
    }

    if (tableContainer) {
        tableContainer.addEventListener('click', (e) => {
            const titleCell = e.target.closest('.title-cell');
            if (!titleCell) return;
            const row = titleCell.closest('.checklist-row');
            const id = row.querySelector('.checklist-checkbox').dataset.id;
            openViewChecklist(id);
        });
    }

    // === Кнопка удаления выбранных чек-листов ===
    const btnDeleteSelected = document.getElementById('openDeleteChecklistBtn');

    function updateDeleteButton() {
        if (!btnDeleteSelected || !tableContainer) return;
        const checked = tableContainer.querySelectorAll('.checklist-checkbox:checked');
        btnDeleteSelected.disabled = checked.length === 0;
    }

    // Обновление состояния кнопки при изменении чекбоксов
    if (tableContainer) {
        tableContainer.addEventListener('change', updateDeleteButton);
    }
    if (selectAll) {
        selectAll.addEventListener('change', updateDeleteButton);
    }

    // Обработчик удаления
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