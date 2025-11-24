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

    // === ЭЛЕМЕНТЫ ДЛЯ ВКЛАДКИ "ФАЙЛЫ ЛОГОВ" ===
    const dropdownContainer = document.querySelector('.log-files-dropdown');
    const btnToggleLogFiles = document.getElementById('toggleLogFiles');
    const logFilesList = document.getElementById('logFilesList');
    const logsDisplayArea = document.getElementById('logsDisplayArea');
    const btnClearOpenedLogs = document.getElementById('btnClearOpenedLogs');
    const btnUpdateLogs = document.getElementById('btnUpdateLogs');
    const fileLogSearchInput = document.getElementById('fileLogSearch');
    const btnSearchFileLogs = document.getElementById('btnSearchFileLogs');
    
    let currentLogFile = null;
    let fileLogsLoaded = false;

    function loadLogFileList() {
        if (!logFilesList) return;

        fetch('/admin/api/logs/files')
            .then(res => {
                if (!res.ok) throw new Error('Не удалось загрузить список файлов');
                return res.json();
            })
            .then(files => {
                logFilesList.innerHTML = '';
                files.forEach(file => {
                    const div = document.createElement('div');
                    div.className = 'log-file-item';
                    div.textContent = file;
                    div.title = file;
                    div.addEventListener('click', (e) => {
                        e.stopPropagation();
                        openLogFile(file);
                        logFilesList.classList.remove('show');
                    });
                    logFilesList.appendChild(div);
                });
            })
            .catch(err => {
                console.error('Ошибка загрузки списка логов:', err);
                logFilesList.innerHTML = '<div style="color:red; padding:8px;">Ошибка загрузки файлов</div>';
            });
    }

    function openLogFile(filename) {
        fetch(`/admin/api/logs/files/${encodeURIComponent(filename)}`)
            .then(res => {
                if (!res.ok) throw new Error(`Файл не найден: ${filename}`);
                return res.text();
            })
            .then(content => {
                currentLogFile = { filename, content };
                renderOpenedLogs();
            })
            .catch(err => {
                console.error(`Ошибка загрузки лога ${filename}:`, err);
                alert(`Не удалось загрузить файл: ${filename}`);
            });
    }

    function renderOpenedLogs() {
        if (!logsDisplayArea) return;

        if (!currentLogFile) {
            logsDisplayArea.innerHTML = '<em>Нет открытых логов</em>';
            if (btnClearOpenedLogs) btnClearOpenedLogs.disabled = true;
            if (btnUpdateLogs) btnUpdateLogs.disabled = true;
            return;
        }

        const { filename, content } = currentLogFile;
        const lines = content.split('\n').filter(line => line.trim() !== '');
        let html = `<div class="log-file-section"><h5>📁 ${filename}</h5>`;

        lines.forEach(line => {
            let className = 'log-entry';
            const lowerLine = line.toLowerCase();
            if (lowerLine.includes('error')) {
                className += ' error';
            } else if (lowerLine.includes('warning') || lowerLine.includes('warn')) {
                className += ' warning';
            }
            html += `<div class="${className}">${escapeHtml(line)}</div>`;
        });

        html += '</div>';
        logsDisplayArea.innerHTML = html;

        // Активируем обе кнопки, если файл открыт
        if (btnClearOpenedLogs) btnClearOpenedLogs.disabled = false;
        if (btnUpdateLogs) btnUpdateLogs.disabled = false;
    }
    function escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '<')
            .replace(/>/g, '>')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function searchInOpenedLogs(query) {
        if (!currentLogFile) {
            logsDisplayArea.innerHTML = '<em>Нет открытого файла для поиска</em>';
            return;
        }

        if (!query.trim()) {
            renderOpenedLogs();
            return;
        }

        const { filename, content } = currentLogFile;
        const term = query.trim();
        const lines = content.split('\n').filter(line => line.trim() !== '');
        const matchedLines = lines.filter(line => line.toLowerCase().includes(term.toLowerCase()));

        let html = `<div class="log-file-section"><h5>📁 ${filename} (${matchedLines.length} совпадений)</h5>`;

        if (matchedLines.length === 0) {
            html += '<div class="log-entry"><em>Ничего не найдено</em></div>';
        } else {
            matchedLines.forEach(line => {
                let className = 'log-entry';
                const lowerLine = line.toLowerCase();
                if (lowerLine.includes('error')) {
                    className += ' error';
                } else if (lowerLine.includes('warning') || lowerLine.includes('warn')) {
                    className += ' warning';
                }
                const highlighted = line.replace(
                    new RegExp(`(${escapeRegex(term)})`, 'gi'),
                    '<mark style="background:#ffeb3b;color:#000;">$1</mark>'
                );
                html += `<div class="${className}">${escapeHtmlForInner(highlighted)}</div>`;
            });
        }

        html += '</div>';
        logsDisplayArea.innerHTML = html;
    }

    function escapeHtmlForInner(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '<')
            .replace(/>/g, '>')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // Обработчик кнопки dropdown
    if (btnToggleLogFiles) {
        btnToggleLogFiles.addEventListener('click', (e) => {
            e.stopPropagation();
            logFilesList.classList.toggle('show');
            if (logFilesList.classList.contains('show') && !fileLogsLoaded) {
                loadLogFileList();
                fileLogsLoaded = true;
            }
        });
    }

    // Закрытие dropdown по клику вне
    document.addEventListener('click', (e) => {
        if (dropdownContainer && !dropdownContainer.contains(e.target)) {
            logFilesList.classList.remove('show');
        }
    });

    // Поиск по логам
    if (btnSearchFileLogs) {
        btnSearchFileLogs.addEventListener('click', () => {
            searchInOpenedLogs(fileLogSearchInput?.value || '');
        });
    }

    if (fileLogSearchInput) {
        fileLogSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchInOpenedLogs(fileLogSearchInput.value);
            }
        });
    }

    // Очистка логов в файле
    if (btnClearOpenedLogs) {
        btnClearOpenedLogs.addEventListener('click', () => {
            if (!currentLogFile) {
                alert('Нет открытого файла для очистки');
                return;
            }

            const filename = currentLogFile.filename;
            if (!confirm(`Очистить содержимое файла "${filename}" на сервере? Это действие нельзя отменить.`)) {
                return;
            }

            fetch(`/admin/api/logs/files/${encodeURIComponent(filename)}/clear`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(async res => {
                const data = await res.json();
                if (res.ok) {
                    alert(`Файл "${filename}" успешно очищен`);
                    // Обновляем отображение: делаем файл пустым
                    currentLogFile.content = '';
                    renderOpenedLogs();
                } else {
                    alert(`Ошибка: ${data.error || 'Не удалось очистить файл'}`);
                }
            })
            .catch(err => {
                console.error('Ошибка при очистке лога:', err);
                alert('Сетевая ошибка при очистке файла');
            });
        });
    }

    // Обновление текущего лог-файла без подтверждений и уведомлений
    if (btnUpdateLogs) {
        btnUpdateLogs.addEventListener('click', () => {
            if (currentLogFile?.filename) {
                openLogFile(currentLogFile.filename);
            }
        });
    
    
    }

    

    // === ЭЛЕМЕНТЫ УПРАВЛЕНИЯ ДЛЯ ВКЛАДКИ "ПОЛЬЗОВАТЕЛИ" ===
    const tableBody = document.querySelector('#usersTable tbody');
    const selectAll = document.getElementById('selectAll');
    const btnDeleteSelected = document.getElementById('btnDeleteSelected');
    const btnDeleteOld = document.getElementById('btnDeleteOld');
    const btnEditRoleSelected = document.getElementById('btnEditRoleSelected');
    const btnExitUserProfole = document.getElementById('btnExitUserProfole');
    const btnDeleteToken = document.getElementById('btnDeleteToken');
    const searchInput = document.getElementById('userSearch');
    const btnSearch = document.getElementById('btnSearch');

    const tooltips = {
        btnDeleteOld: "Удалить все НЕПОДТВЕРЖДЁННЫЕ (по отправленной ссылке на email) аккаунты старше 24 часов",
        btnDeleteSelected: "Удалить пользователей и всю их персональную информацию. Их созданные товары в магазине сохранятся, но станут анонимными. Токены отзываются (не удаляются!)",
        btnEditRoleSelected: "Изменить роль выбранного пользователя",
        btnExitUserProfole: "Отозвать токены выбранных пользователей (завершить сессии)",
        btnDeleteToken: "Очистить из базы только ПРОСРОЧЕННЫЕ токены. Активные и отозванные токены сохраняются для безопасности."
    };

    Object.entries(tooltips).forEach(([id, text]) => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.title = text;
        }
    });

    let roleDropdown = null;

    function createRoleDropdown() {
        if (roleDropdown) return;

        roleDropdown = document.createElement('div');
        roleDropdown.className = 'role-select-dropdown';

        ['admin', 'suser', 'user', 'tester'].forEach(role => {
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

    function loadUsers() {
        fetch('/admin/api/users')
            .then(res => res.json())
            .then(users => {
                renderUsers(users);
            })
            .catch(err => {
                console.error('Ошибка загрузки пользователей:', err);
                if (tableBody) {
                    tableBody.innerHTML = '<tr><td colspan="10">Ошибка загрузки</td></tr>';
                }
            });
    }

    function renderUsers(users) {
        if (!tableBody) return;

        tableBody.innerHTML = '';
        if (users.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="10">Нет данных</td></tr>';
            updateButtons();
            return;
        }

        users.forEach(user => {
            const row = document.createElement('tr');
            row.className = user.confirm_email ? 'confirmed' : 'not-confirmed';

            const confirmedText = user.confirm_email ? '✅ Да' : '❌ Нет';
            const dateText = user.created_at
                ? new Date(user.created_at).toLocaleString('ru-RU')
                : '—';

            const roleText = user.role || '—';
            const userAgentText = user.user_agent || '—';

            const sessionText = user.session_minutes_left !== null
                ? `${user.session_minutes_left} мин`
                : '—';

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
                <td>${sessionText}</td>
            `;
            tableBody.appendChild(row);
        });
        updateButtons();
    }

    function updateButtons() {
        const checked = document.querySelectorAll('.user-checkbox:checked');
        const checkedCount = checked.length;

        if (btnDeleteSelected) {
            btnDeleteSelected.disabled = checkedCount === 0;
        }

        if (btnEditRoleSelected) {
            btnEditRoleSelected.disabled = checkedCount !== 1;
        }

        if (btnExitUserProfole) {
            btnExitUserProfole.disabled = checkedCount === 0;
        }

        if (btnDeleteToken) {
            btnDeleteToken.disabled = false;
        }
    }

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
                    tableBody.innerHTML = '<tr><td colspan="10">Ошибка поиска</td></tr>';
                }
            });
    }

    btnSearch?.addEventListener('click', () => {
        searchUsers(searchInput?.value || '');
    });

    searchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchUsers(searchInput.value);
        }
    });

    document.addEventListener('click', function(e) {
        const button = e.target.closest('.copy-email-btn');
        if (!button) return;

        const email = button.getAttribute('data-email');
        if (!email) {
            console.warn('Кнопка копирования не содержит data-email');
            return;
        }

        const originalText = button.textContent;

        navigator.clipboard.writeText(email)
            .then(() => {
                button.textContent = '✓';
                setTimeout(() => {
                    button.textContent = originalText;
                }, 1000);
            })
            .catch(err => {
                console.error('Ошибка копирования email:', err);
                alert('Не удалось скопировать email. Возможно, сайт не использует HTTPS или браузер блокирует clipboard.');
            });
    });
    
    selectAll?.addEventListener('change', () => {
        document.querySelectorAll('.user-checkbox:not(:disabled)').forEach(cb => {
            cb.checked = selectAll.checked;
        });
        updateButtons();
    });

    if (tableBody) {
        tableBody.addEventListener('change', updateButtons);
    }

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

    btnExitUserProfole?.addEventListener('click', () => {
        const checkedBoxes = document.querySelectorAll('.user-checkbox:checked');
        const user_ids = Array.from(checkedBoxes).map(cb => cb.dataset.id);

        if (user_ids.length === 0) {
            alert('Выберите хотя бы одного пользователя');
            return;
        }

        if (!confirm(`Завершить сессии для ${user_ids.length} пользователей? Это отключит их от всех устройств.`)) {
            return;
        }

        fetch('/admin/api/users/revoke-sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_ids })
        })
        .then(async res => {
            try {
                const data = await res.json();
                if (res.ok) {
                    alert(`Сессии успешно завершены для ${user_ids.length} пользователей`);
                    loadUsers();
                } else {
                    alert(`Ошибка: ${data.error || 'Не удалось завершить сессии'}`);
                }
            } catch (e) {
                alert('Ошибка: не удалось обработать ответ сервера');
            }
        })
        .catch(err => {
            console.error('Сетевая ошибка при завершении сессий:', err);
            alert('Ошибка сети при завершении сессий');
        });
    });

    btnDeleteToken?.addEventListener('click', () => {
        const checkedBoxes = document.querySelectorAll('.user-checkbox:checked');
        const user_ids = Array.from(checkedBoxes).map(cb => cb.dataset.id);

        let confirmMsg, fetchBody;

        if (user_ids.length > 0) {
            confirmMsg = `Удалить только ПРОСРОЧЕННЫЕ токены для ${user_ids.length} пользователей? Активные и отозванные токены сохранятся.`;
            fetchBody = { user_ids };
        } else {
            confirmMsg = 'Удалить ВСЕ ПРОСРОЧЕННЫЕ токены из базы? Это безопасно: активные сессии не затронуты, отозванные токены останутся для защиты.';
        }

        if (!confirm(confirmMsg)) return;

        fetch('/admin/api/users/delete-tokens', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(fetchBody)
        })
        .then(async res => {
            try {
                const data = await res.json();
                if (res.ok) {
                    const successMsg = user_ids.length > 0
                        ? `Удалено просроченных токенов для ${user_ids.length} пользователей`
                        : `Удалено ${data.deleted_count} просроченных токенов`;
                    alert(successMsg);
                    // loadUsers(); — не обязателен, т.к. сессии не меняются
                } else {
                    alert(`Ошибка: ${data.error || 'Не удалось очистить токены'}`);
                }
            } catch (e) {
                alert('Ошибка: не удалось обработать ответ сервера');
            }
        })
        .catch(err => {
            console.error('Сетевая ошибка при очистке токенов:', err);
            alert('Ошибка сети при очистке токенов');
        });
    });

    // === ЭЛЕМЕНТЫ ДЛЯ ВКЛАДКИ "ЛОГИ" ===
    const logsTableBody = document.querySelector('#logsTable tbody');
    const selectAllLogs = document.getElementById('selectAllLogs');
    const btnBlockSelected = document.getElementById('btnBlockSelected');
    const btnUnblockSelected = document.getElementById('btnUnblockSelected');
    const logSearchInput = document.getElementById('logSearch');
    const btnSearchLogs = document.getElementById('btnSearchLogs');

    function loadLogs() {
        if (!logsTableBody) return;
        logsTableBody.innerHTML = '<tr><td colspan="5">Загрузка...</td></tr>';

        fetch('/admin/api/logs')
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.json();
            })
            .then(logs => {
                renderLogs(logs);
            })
            .catch(err => {
                console.error('Ошибка загрузки логов:', err);
                logsTableBody.innerHTML = '<tr><td colspan="5">Ошибка загрузки</td></tr>';
            });
    }

    function renderLogs(logs) {
        if (!logsTableBody) return;
        logsTableBody.innerHTML = '';

        if (!Array.isArray(logs) || logs.length === 0) {
            logsTableBody.innerHTML = '<tr><td colspan="5">Нет записей</td></tr>';
            updateLogButtons();
            return;
        }

        logs.forEach(log => {
            const userIdDisplay = log.user_id !== null ? log.user_id : '—';
            const blockedText = log.is_blocked ? '✅ Да' : '❌ Нет';

            const row = document.createElement('tr');
            row.className = log.is_blocked ? 'ip-blocked' : 'ip-not-blocked';
            row.innerHTML = `
                <td>
                    <input type="checkbox" class="log-checkbox" 
                        data-ip="${log.ip_address}"
                        data-blocked="${log.is_blocked}">
                </td>
                <td>${userIdDisplay}</td>
                <td>${log.ip_address}</td>
                <td>${log.recovery_attempts_count}</td>
                <td>${blockedText}</td>
            `;
            logsTableBody.appendChild(row);
        });
        updateLogButtons();
    }

    function searchLogs(query) {
        if (!query.trim()) {
            loadLogs();
            return;
        }

        let isBlockedParam = null;
        const lowerQuery = query.trim().toLowerCase();
        if (lowerQuery === 'да') {
            isBlockedParam = true;
        } else if (lowerQuery === 'нет') {
            isBlockedParam = false;
        }

        const url = new URL('/admin/api/logs/search', window.location.origin);
        url.searchParams.append('q', query);
        if (isBlockedParam !== null) {
            url.searchParams.append('is_blocked', isBlockedParam);
        }

        fetch(url)
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.json();
            })
            .then(logs => {
                renderLogs(logs);
            })
            .catch(err => {
                console.error('Ошибка поиска логов:', err);
                logsTableBody.innerHTML = '<tr><td colspan="5">Ошибка поиска</td></tr>';
            });
    }

    function updateLogButtons() {
        const checked = document.querySelectorAll('.log-checkbox:checked');
        const hasSelected = checked.length > 0;
        
        if (btnBlockSelected) {
            btnBlockSelected.disabled = !hasSelected;
        }
        if (btnUnblockSelected) {
            btnUnblockSelected.disabled = !hasSelected;
        }
    }

    if (selectAllLogs) {
        selectAllLogs.addEventListener('change', () => {
            document.querySelectorAll('.log-checkbox:not(:disabled)').forEach(cb => {
                cb.checked = selectAllLogs.checked;
            });
            updateLogButtons();
        });
    }

    if (logsTableBody) {
        logsTableBody.addEventListener('change', updateLogButtons);
    }

    if (btnSearchLogs) {
        btnSearchLogs.addEventListener('click', () => {
            searchLogs(logSearchInput?.value || '');
        });
    }
    if (logSearchInput) {
        logSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchLogs(logSearchInput.value);
            }
        });
    }

    if (btnBlockSelected) {
        btnBlockSelected.addEventListener('click', () => {
            const ips = Array.from(document.querySelectorAll('.log-checkbox:checked'))
                .map(cb => cb.dataset.ip);

            if (ips.length === 0) {
                alert('Выберите записи для блокировки');
                return;
            }

            const uniqueIps = [...new Set(ips)];

            if (!confirm(`Заблокировать вход с ${uniqueIps.length} IP-адрес(а/ов)?`)) return;

            fetch('/admin/api/logs/block', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip_addresses: uniqueIps })
            })
            .then(async res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                const data = await res.json();
                alert(`Заблокировано: ${data.blocked_count} записей`);
                loadLogs();
            })
            .catch(err => {
                console.error('Ошибка блокировки:', err);
                alert('Ошибка сети или сервера при блокировке');
            });
        });
    }

    if (btnUnblockSelected) {
        btnUnblockSelected.addEventListener('click', () => {
            const ips = Array.from(document.querySelectorAll('.log-checkbox:checked'))
                .map(cb => cb.dataset.ip);

            if (ips.length === 0) {
                alert('Выберите записи для разблокировки');
                return;
            }

            const uniqueIps = [...new Set(ips)];

            if (!confirm(`Разблокировать вход с ${uniqueIps.length} IP-адрес(а/ов)?`)) return;

            fetch('/admin/api/logs/unblock', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip_addresses: uniqueIps })
            })
            .then(async res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                const data = await res.json();
                alert(`Разблокировано: ${data.unblocked_count || uniqueIps.length} IP-адресов`);
                loadLogs();
            })
            .catch(err => {
                console.error('Ошибка разблокировки:', err);
                alert('Ошибка сети или сервера при разблокировке');
            });
        });
    }

    loadUsers();
});