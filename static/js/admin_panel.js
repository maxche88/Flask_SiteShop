document.addEventListener('DOMContentLoaded', () => {
    // === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
    function showInfo(message, type = 'info', target = 'users') {
        const id = target === 'logs' ? 'admin-info-panel-logs' : 'admin-info-panel';
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = message;
        el.className = `admin-info-message ${type}`;
        el.classList.remove('hidden');
        // Скрываем info/warning/success через 5 сек
        if (type !== 'error') {
            setTimeout(() => {
                if (el && !el.classList.contains('hidden')) {
                    el.classList.add('hidden');
                }
            }, 5000);
        }
    }

    function hideInfo(target = 'users') {
        const id = target === 'logs' ? 'admin-info-panel-logs' : 'admin-info-panel';
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    }

    function clearTable(container) {
        container.innerHTML = '';
    }

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
            hideInfo('users');
            hideInfo('logs');
            if (target === 'logs' && !window.logsLoaded) {
                loadLogs();
                window.logsLoaded = true;
            }
        });
    });

    // === ФАЙЛОВЫЕ ЛОГИ ===
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
        if (btnClearOpenedLogs) btnClearOpenedLogs.disabled = false;
        if (btnUpdateLogs) btnUpdateLogs.disabled = false;
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
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
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

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

    document.addEventListener('click', (e) => {
        if (dropdownContainer && !dropdownContainer.contains(e.target)) {
            logFilesList.classList.remove('show');
        }
    });

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

    if (btnClearOpenedLogs) {
        btnClearOpenedLogs.addEventListener('click', () => {
            if (!currentLogFile) return;
            const filename = currentLogFile.filename;
            if (!confirm(`Очистить содержимое файла "${filename}" на сервере? Это действие нельзя отменить.`)) {
                return;
            }
            fetch(`/admin/api/logs/files/${encodeURIComponent(filename)}/clear`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(async res => {
                const data = await res.json();
                if (res.ok) {
                    currentLogFile.content = '';
                    renderOpenedLogs();
                }
            })
            .catch(err => {
                console.error('Ошибка при очистке лога:', err);
            });
        });
    }

    if (btnUpdateLogs) {
        btnUpdateLogs.addEventListener('click', () => {
            if (currentLogFile?.filename) {
                openLogFile(currentLogFile.filename);
            }
        });
    }

    // === УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ===
    const usersListContainer = document.getElementById('users-list');
    const selectAllUsers = document.getElementById('select-all-users');
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
        if (btn) btn.title = text;
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
        if (roleDropdown) roleDropdown.style.display = 'none';
    }

    function selectRole(newRole) {
        hideRoleDropdown();
        const checkedBoxes = usersListContainer.querySelectorAll('.admin-checkbox:checked');
        if (checkedBoxes.length === 0) {
            showInfo('Не выбрано ни одного пользователя', 'warning', 'users');
            return;
        }
        if (checkedBoxes.length > 1) {
            showInfo('За один раз можно изменить роль только одному пользователю.', 'warning', 'users');
            return;
        }
        const userId = checkedBoxes[0].closest('.user-row').dataset.userId;
        if (!confirm(`Изменить роль пользователя ID ${userId} на "${newRole}"?`)) return;

        fetch(`/admin/api/users/${userId}/role`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: newRole })
        })
        .then(async res => {
            const data = await res.json();
            if (res.ok) {
                showInfo(`Роль успешно изменена на "${newRole}"`, 'success', 'users');
                loadUsers();
            } else {
                showInfo(`Ошибка: ${data.error || 'Неизвестная ошибка'}`, 'error', 'users');
            }
        })
        .catch(err => {
            console.error('Сетевая ошибка:', err);
            showInfo('Ошибка сети при изменении роли', 'error', 'users');
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
        showInfo('Загрузка...', 'info', 'users');
        clearTable(usersListContainer);
        fetch('/admin/api/users')
            .then(res => res.json())
            .then(users => {
                renderUsers(users);
            })
            .catch(err => {
                console.error('Ошибка загрузки пользователей:', err);
                clearTable(usersListContainer);
                showInfo('Не удалось загрузить пользователей', 'error', 'users');
            });
    }

    function renderUsers(users) {
        clearTable(usersListContainer);
        if (!Array.isArray(users) || users.length === 0) {
            showInfo('Нет данных', 'info', 'users');
            updateButtons();
            return;
        }
        showInfo(''); // скрыть предыдущее сообщение
        const template = document.getElementById('user-row-template');
        users.forEach(user => {
            const row = template.content.cloneNode(true).querySelector('.admin-row');
            row.dataset.userId = user.id;
            row.querySelector('.id-col').textContent = user.id;
            row.querySelector('.username').textContent = user.username;
            const emailCell = row.querySelector('.email-col');
            emailCell.innerHTML = `
                <div class="email-cell">
                    <span class="email-text">${user.email}</span>
                    <button class="copy-email-btn" data-email="${user.email}" title="Копировать email">📋</button>
                </div>
            `;
            row.querySelector('.verified-col').textContent = user.confirm_email ? '✅ Да' : '❌ Нет';
            row.querySelector('.date-col').textContent = user.created_at
                ? new Date(user.created_at).toLocaleString('ru-RU')
                : '—';
            row.querySelector('.ip-col').textContent = user.ip_logs_count || 0;
            row.querySelector('.role-col').textContent = user.role || '—';
            row.querySelector('.device-col').textContent = user.user_agent || '—';
            row.querySelector('.session-col').textContent = user.session_minutes_left !== null
                ? `${user.session_minutes_left} мин`
                : '—';
            usersListContainer.appendChild(row);
        });
        updateButtons();
    }

    function updateButtons() {
        const checked = usersListContainer.querySelectorAll('.admin-checkbox:checked');
        const count = checked.length;
        btnDeleteSelected.disabled = count === 0;
        btnEditRoleSelected.disabled = count !== 1;
        btnExitUserProfole.disabled = count === 0;
        btnDeleteToken.disabled = false;
    }

    function searchUsers(query) {
        if (!query.trim()) {
            loadUsers();
            return;
        }
        showInfo('Поиск...', 'info', 'users');
        clearTable(usersListContainer);
        fetch(`/admin/api/users/search?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(users => renderUsers(users))
            .catch(err => {
                console.error('Ошибка поиска:', err);
                clearTable(usersListContainer);
                showInfo('Ошибка при поиске пользователей', 'error', 'users');
            });
    }

    btnSearch?.addEventListener('click', () => searchUsers(searchInput?.value || ''));
    searchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchUsers(searchInput.value);
    });

    usersListContainer.addEventListener('click', (e) => {
        const button = e.target.closest('.copy-email-btn');
        if (!button) return;
        const email = button.getAttribute('data-email');
        if (!email) return;
        const originalText = button.textContent;
        navigator.clipboard.writeText(email)
            .then(() => {
                button.textContent = '✓';
                setTimeout(() => button.textContent = originalText, 1000);
            })
            .catch(err => {
                console.error('Ошибка копирования email:', err);
                showInfo('Не удалось скопировать email', 'error', 'users');
            });
    });

    selectAllUsers?.addEventListener('change', () => {
        usersListContainer.querySelectorAll('.admin-checkbox').forEach(cb => {
            cb.checked = selectAllUsers.checked;
        });
        updateButtons();
    });

    usersListContainer.addEventListener('change', updateButtons);

    btnDeleteSelected?.addEventListener('click', () => {
        const ids = Array.from(usersListContainer.querySelectorAll('.admin-checkbox:checked'))
            .map(cb => cb.closest('.user-row').dataset.userId);
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
                showInfo(`Удалено: ${data.deleted_count} пользователей`, 'success', 'users');
                loadUsers();
            } else {
                showInfo('Ошибка при удалении', 'error', 'users');
            }
        })
        .catch(err => {
            console.error('Ошибка удаления:', err);
            showInfo('Произошла ошибка при удалении', 'error', 'users');
        });
    });

    btnDeleteOld?.addEventListener('click', () => {
        if (!confirm('Удалить ВСЕ неподтверждённые аккаунты старше 24 часов?')) return;
        fetch('/admin/api/users/delete-old-unconfirmed', { method: 'DELETE' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showInfo(`Удалено: ${data.deleted_count} пользователей`, 'success', 'users');
                    loadUsers();
                } else {
                    showInfo('Ошибка при удалении старых аккаунтов', 'error', 'users');
                }
            })
            .catch(err => {
                console.error('Ошибка удаления старых:', err);
                showInfo('Произошла ошибка', 'error', 'users');
            });
    });

    btnExitUserProfole?.addEventListener('click', () => {
        const user_ids = Array.from(usersListContainer.querySelectorAll('.admin-checkbox:checked'))
            .map(cb => cb.closest('.user-row').dataset.userId);
        if (user_ids.length === 0) {
            showInfo('Выберите хотя бы одного пользователя', 'warning', 'users');
            return;
        }
        if (!confirm(`Завершить сессии для ${user_ids.length} пользователей? Это отключит их от всех устройств.`)) return;

        fetch('/admin/api/users/revoke-sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_ids })
        })
        .then(async res => {
            const data = await res.json();
            if (res.ok) {
                showInfo(`Сессии успешно завершены для ${user_ids.length} пользователей`, 'success', 'users');
                loadUsers();
            } else {
                showInfo(`Ошибка: ${data.error || 'Не удалось завершить сессии'}`, 'error', 'users');
            }
        })
        .catch(err => {
            console.error('Сетевая ошибка при завершении сессий:', err);
            showInfo('Ошибка сети при завершении сессий', 'error', 'users');
        });
    });

    btnDeleteToken?.addEventListener('click', () => {
        const user_ids = Array.from(usersListContainer.querySelectorAll('.admin-checkbox:checked'))
            .map(cb => cb.closest('.user-row').dataset.userId);

        let confirmMsg;
        if (user_ids.length > 0) {
            confirmMsg = `Удалить только ПРОСРОЧЕННЫЕ токены для ${user_ids.length} пользователей? Активные и отозванные токены сохранятся.`;
        } else {
            confirmMsg = 'Удалить ВСЕ ПРОСРОЧЕННЫЕ токены из базы? Это безопасно: активные сессии не затронуты, отозванные токены останутся для защиты.';
        }

        if (!confirm(confirmMsg)) return;

        fetch('/admin/api/users/delete-tokens', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(user_ids.length > 0 ? { user_ids } : {})
        })
        .then(async res => {
            const data = await res.json();
            if (res.ok) {
                const msg = user_ids.length > 0
                    ? `Удалено просроченных токенов для ${user_ids.length} пользователей`
                    : `Удалено ${data.deleted_count} просроченных токенов`;
                showInfo(msg, 'success', 'users');
            } else {
                showInfo(`Ошибка: ${data.error || 'Не удалось очистить токены'}`, 'error', 'users');
            }
        })
        .catch(err => {
            console.error('Сетевая ошибка при очистке токенов:', err);
            showInfo('Ошибка сети при очистке токенов', 'error', 'users');
        });
    });

    // === БЛОКИРОВКА IP ===
    const logsListContainer = document.getElementById('logs-list');
    const selectAllLogs = document.getElementById('select-all-logs');
    const btnBlockSelected = document.getElementById('btnBlockSelected');
    const btnUnblockSelected = document.getElementById('btnUnblockSelected');
    const logSearchInput = document.getElementById('logSearch');
    const btnSearchLogs = document.getElementById('btnSearchLogs');

    function loadLogs() {
        showInfo('Загрузка...', 'info', 'logs');
        clearTable(logsListContainer);
        fetch('/admin/api/ip_logs')
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.json();
            })
            .then(logs => renderLogs(logs))
            .catch(err => {
                console.error('Ошибка загрузки логов:', err);
                clearTable(logsListContainer);
                showInfo('Не удалось загрузить IP-логи', 'error', 'logs');
            });
    }

    function renderLogs(logs) {
        clearTable(logsListContainer);
        if (!Array.isArray(logs) || logs.length === 0) {
            showInfo('Нет записей', 'info', 'logs');
            updateLogButtons();
            return;
        }
        showInfo(''); // скрыть предыдущее
        const template = document.getElementById('log-row-template');
        logs.forEach(log => {
            const row = template.content.cloneNode(true).querySelector('.admin-row');
            row.dataset.ipAddress = log.ip_address;
            row.querySelector('.id-col').textContent = log.user_id ?? '—';
            row.querySelector('.ip-col').textContent = log.ip_address;
            row.querySelector('.attempts-col').textContent = log.recovery_attempts_count;
            row.querySelector('.blocked-col').textContent = log.is_blocked ? '✅ Да' : '❌ Нет';
            logsListContainer.appendChild(row);
        });
        updateLogButtons();
    }

    function searchLogs(query) {
        if (!query.trim()) {
            loadLogs();
            return;
        }
        showInfo('Поиск...', 'info', 'logs');
        clearTable(logsListContainer);
        let isBlockedParam = null;
        const lowerQuery = query.trim().toLowerCase();
        if (lowerQuery === 'да') isBlockedParam = true;
        else if (lowerQuery === 'нет') isBlockedParam = false;

        const url = new URL('/admin/api/ip_logs/search', window.location.origin);
        url.searchParams.append('q', query);
        if (isBlockedParam !== null) url.searchParams.append('is_blocked', isBlockedParam);

        fetch(url)
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.json();
            })
            .then(logs => renderLogs(logs))
            .catch(err => {
                console.error('Ошибка поиска логов:', err);
                clearTable(logsListContainer);
                showInfo('Ошибка при поиске IP-записей', 'error', 'logs');
            });
    }

    function updateLogButtons() {
        const checked = logsListContainer.querySelectorAll('.admin-checkbox:checked');
        const hasSelected = checked.length > 0;
        btnBlockSelected.disabled = !hasSelected;
        btnUnblockSelected.disabled = !hasSelected;
    }

    selectAllLogs?.addEventListener('change', () => {
        logsListContainer.querySelectorAll('.admin-checkbox').forEach(cb => {
            cb.checked = selectAllLogs.checked;
        });
        updateLogButtons();
    });

    logsListContainer.addEventListener('change', updateLogButtons);

    btnSearchLogs?.addEventListener('click', () => searchLogs(logSearchInput?.value || ''));
    logSearchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchLogs(logSearchInput.value);
    });

    btnBlockSelected?.addEventListener('click', () => {
        const ips = Array.from(logsListContainer.querySelectorAll('.admin-checkbox:checked'))
            .map(cb => cb.closest('.ip-row').dataset.ipAddress);
        if (ips.length === 0) {
            showInfo('Выберите записи для блокировки', 'warning', 'logs');
            return;
        }
        const uniqueIps = [...new Set(ips)];
        if (!confirm(`Заблокировать вход с ${uniqueIps.length} IP-адрес(а/ов)?`)) return;

        fetch('/admin/api/ip_logs/block', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip_addresses: uniqueIps })
        })
        .then(async res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            const data = await res.json();
            showInfo(`Заблокировано: ${data.blocked_count} записей`, 'success', 'logs');
            loadLogs();
        })
        .catch(err => {
            console.error('Ошибка блокировки:', err);
            showInfo('Ошибка сети или сервера при блокировке', 'error', 'logs');
        });
    });

    btnUnblockSelected?.addEventListener('click', () => {
        const ips = Array.from(logsListContainer.querySelectorAll('.admin-checkbox:checked'))
            .map(cb => cb.closest('.ip-row').dataset.ipAddress);
        if (ips.length === 0) {
            showInfo('Выберите записи для разблокировки', 'warning', 'logs');
            return;
        }
        const uniqueIps = [...new Set(ips)];
        if (!confirm(`Разблокировать вход с ${uniqueIps.length} IP-адрес(а/ов)?`)) return;

        fetch('/admin/api/ip_logs/unblock', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip_addresses: uniqueIps })
        })
        .then(async res => {
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            const data = await res.json();
            showInfo(`Разблокировано: ${data.unblocked_count || uniqueIps.length} IP-адресов`, 'success', 'logs');
            loadLogs();
        })
        .catch(err => {
            console.error('Ошибка разблокировки:', err);
            showInfo('Ошибка сети или сервера при разблокировке', 'error', 'logs');
        });
    });

    // Загрузка данных при старте
    loadUsers();
});