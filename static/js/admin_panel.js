document.addEventListener('DOMContentLoaded', () => {
    // === ВКЛАДКИ ===
    const tabs = document.querySelectorAll('.admin-tab');
    const tabContents = document.querySelectorAll('.admin-tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const target = tab.dataset.tab;
            document.getElementById(`tab-${target}`).classList.add('active');

            if (target === 'logs' && !window.logsLoaded) {
                loadLogs();
                window.logsLoaded = true;
            }
        });
    });

    // === ЭЛЕМЕНТЫ УПРАВЛЕНИЯ ===
    const tableBody = document.querySelector('#usersTable tbody');
    const selectAll = document.getElementById('selectAll');
    const btnDeleteSelected = document.getElementById('btnDeleteSelected');
    const btnDeleteOld = document.getElementById('btnDeleteOld');
    const btnEditRoleSelected = document.getElementById('btnEditRoleSelected');
    const searchInput = document.getElementById('userSearch');
    const btnSearch = document.getElementById('btnSearch');

    // === ВСПЛЫВАЮЩЕЕ МЕНЮ ДЛЯ ВЫБОРА РОЛИ ===
    let roleDropdown = null;

    function createRoleDropdown() {
        if (roleDropdown) return;

        roleDropdown = document.createElement('div');
        roleDropdown.className = 'role-select-dropdown';

        ['admin', 'suser', 'user'].forEach(role => {
            const item = document.createElement('div');
            item.className = 'role-select-item';
            item.textContent = role;
            item.addEventListener('click', () => selectRole(role));
            roleDropdown.appendChild(item);
        });

        document.body.appendChild(roleDropdown);
    }

    function showRoleDropdown() {
        if (!roleDropdown) createRoleDropdown();

        const buttonRect = btnEditRoleSelected.getBoundingClientRect();
        roleDropdown.style.top = `${buttonRect.bottom + window.scrollY}px`;
        roleDropdown.style.left = `${buttonRect.left + window.scrollX}px`;
        roleDropdown.style.display = 'block';
    }

    function hideRoleDropdown() {
        if (roleDropdown) {
            roleDropdown.style.display = 'none';
        }
    }

    function selectRole(newRole) {
        hideRoleDropdown();

        const checkedBoxes = document.querySelectorAll('.user-checkbox:checked');
        if (checkedBoxes.length === 0) {
            alert('Не выбрано ни одного пользователя');
            return;
        }

        if (checkedBoxes.length > 1) {
            alert('За один раз можно изменить роль только одному пользователю.');
            return;
        }

        const userId = checkedBoxes[0].dataset.id;

        if (!confirm(`Изменить роль пользователя ID ${userId} на "${newRole}"?`)) {
            return;
        }

        fetch(`/admin/api/users/${userId}/role`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: newRole })
        })
        .then(async res => {
            try {
                const data = await res.json();
                if (res.ok) {
                    alert(`Роль успешно изменена на "${newRole}"`);
                    loadUsers();
                } else {
                    alert(`Ошибка: ${data.error || 'Неизвестная ошибка'}`);
                }
            } catch (e) {
                alert('Ошибка: не удалось обработать ответ сервера');
            }
        })
        .catch(err => {
            console.error('Сетевая ошибка:', err);
            alert('Ошибка сети при изменении роли');
        });
    }

    // Обработчики кнопки "Изменить роль"
    btnEditRoleSelected?.addEventListener('click', (e) => {
        e.stopPropagation();
        showRoleDropdown();
    });

    document.addEventListener('click', (e) => {
        if (roleDropdown && 
            !btnEditRoleSelected.contains(e.target) && 
            !roleDropdown.contains(e.target)) {
            hideRoleDropdown();
        }
    });

    // === ФУНКЦИЯ: ЗАГРУЗКА ВСЕХ ПОЛЬЗОВАТЕЛЕЙ ===
    function loadUsers() {
        fetch('/admin/api/users')
            .then(res => res.json())
            .then(users => {
                renderUsers(users);
            })
            .catch(err => {
                console.error('Ошибка загрузки пользователей:', err);
                if (tableBody) {
                    tableBody.innerHTML = '<tr><td colspan="8">Ошибка загрузки</td></tr>';
                }
            });
    }

    // === ФУНКЦИЯ: ОТРИСОВКА СПИСКА ПОЛЬЗОВАТЕЛЕЙ ===
    function renderUsers(users) {
        if (!tableBody) return;

        tableBody.innerHTML = '';
        if (users.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="9">Нет данных</td></tr>';
            updateButtons();
            return;
        }

        users.forEach(user => {
            const row = document.createElement('tr');
            row.className = user.confirm_email ? 'confirmed' :
                (user.is_old_unconfirmed ? 'old-unconfirmed' : '');

            const confirmedText = user.confirm_email ? '✅ Да' : '❌ Нет';
            const dateText = user.created_at
                ? new Date(user.created_at).toLocaleString('ru-RU')
                : '—';

            const roleText = user.role || '—';
            const userAgentText = user.user_agent || '—';

            row.innerHTML = `
                <td>
                    <input type="checkbox" class="user-checkbox" data-id="${user.id}">
                </td>
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>
                    <div class="email-cell">
                        <span class="email-text">${user.email}</span>
                        <button class="copy-email-btn" data-email="${user.email}" title="Копировать email">📋</button>
                    </div>
                </td>
                <td>${confirmedText}</td>
                <td>${dateText}</td>
                <td>${user.ip_logs_count || 0}</td>
                <td>${roleText}</td>
                <td>${userAgentText}</td>
            `;
            tableBody.appendChild(row);
        });
        updateButtons();
    }

    // === ОБНОВЛЕНИЕ СОСТОЯНИЯ КНОПОК ===
    function updateButtons() {
        const checked = document.querySelectorAll('.user-checkbox:checked');
        const checkedCount = checked.length;

        if (btnDeleteSelected) {
            btnDeleteSelected.disabled = checkedCount === 0;
        }

        if (btnEditRoleSelected) {
            btnEditRoleSelected.disabled = checkedCount !== 1;
        }
    }

    // === ПОИСК ===
    function searchUsers(query) {
        if (!query.trim()) {
            loadUsers();
            return;
        }

        fetch(`/admin/api/users/search?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(users => {
                renderUsers(users);
            })
            .catch(err => {
                console.error('Ошибка поиска:', err);
                if (tableBody) {
                    tableBody.innerHTML = '<tr><td colspan="8">Ошибка поиска</td></tr>';
                }
            });
    }

    // === ОБРАБОТЧИКИ ПОИСКА ===
    btnSearch?.addEventListener('click', () => {
        searchUsers(searchInput?.value || '');
    });

    searchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchUsers(searchInput.value);
        }
    });

    // === КОПИРОВАНИЕ EMAIL ===
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('copy-email-btn')) {
            const email = e.target.dataset.email;
            if (!email) return;

            navigator.clipboard.writeText(email)
                .then(() => {
                    const original = e.target.textContent;
                    e.target.textContent = '✓';
                    setTimeout(() => e.target.textContent = original, 1000);
                })
                .catch(() => alert('Не удалось скопировать email'));
        }
    });

    // === УПРАВЛЕНИЕ ЧЕКБОКСАМИ ===
    selectAll?.addEventListener('change', () => {
        document.querySelectorAll('.user-checkbox:not(:disabled)').forEach(cb => {
            cb.checked = selectAll.checked;
        });
        updateButtons();
    });

    if (tableBody) {
        tableBody.addEventListener('change', updateButtons);
    }

    // === УДАЛЕНИЕ ===
    btnDeleteSelected?.addEventListener('click', () => {
        const ids = Array.from(document.querySelectorAll('.user-checkbox:checked'))
            .map(cb => cb.dataset.id);

        if (ids.length === 0) return;
        if (!confirm(`Удалить ${ids.length} пользователей и их IP-записи?`)) return;

        fetch('/admin/api/users/delete-selected', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_ids: ids })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(`Удалено: ${data.deleted_count} пользователей`);
                loadUsers();
            } else {
                alert('Ошибка при удалении');
            }
        })
        .catch(err => {
            console.error('Ошибка удаления:', err);
            alert('Произошла ошибка при удалении');
        });
    });

    // === УДАЛЕНИЕ СТАРЫХ НЕПОДТВЕРЖДЁННЫХ ===
    btnDeleteOld?.addEventListener('click', () => {
        if (!confirm('Удалить ВСЕ неподтверждённые аккаунты старше 24 часов?')) return;

        fetch('/admin/api/users/delete-old-unconfirmed', {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(`Удалено: ${data.deleted_count} пользователей`);
                loadUsers();
            } else {
                alert('Ошибка при удалении старых аккаунтов');
            }
        })
        .catch(err => {
            console.error('Ошибка удаления старых:', err);
            alert('Произошла ошибка');
        });
    });



    // === ИНИЦИАЛИЗАЦИЯ ===
    loadUsers();
});