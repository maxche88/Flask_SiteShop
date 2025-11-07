document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector('#usersTable tbody');
    const selectAll = document.getElementById('selectAll');
    const btnDeleteSelected = document.getElementById('btnDeleteSelected');
    const btnDeleteOld = document.getElementById('btnDeleteOld');

    // Загрузка данных
    function loadUsers() {
        fetch('/admin/api/users')
            .then(res => res.json())
            .then(users => {
                tableBody.innerHTML = '';
                users.forEach(user => {
                    const row = document.createElement('tr');
                    row.className = user.confirm_email ? 'confirmed' : 
                                    user.is_old_unconfirmed ? 'old-unconfirmed' : '';

                    const confirmedText = user.confirm_email ? '✅ Да' : '❌ Нет';
                    const dateText = user.created_at 
                        ? new Date(user.created_at).toLocaleString('ru-RU') 
                        : '—';

                    row.innerHTML = `
                        <td><input type="checkbox" class="user-checkbox" 
                            data-id="${user.id}" ${user.confirm_email ? 'disabled' : ''}></td>
                        <td>${user.id}</td>
                        <td>${user.username}</td>
                        <td>${user.email}</td>
                        <td>${confirmedText}</td>
                        <td>${dateText}</td>
                        <td>${user.ip_logs_count}</td>
                    `;
                    tableBody.appendChild(row);
                });
                updateDeleteButton();
            })
            .catch(err => {
                console.error('Ошибка загрузки пользователей:', err);
                tableBody.innerHTML = '<tr><td colspan="7">Ошибка загрузки</td></tr>';
            });
    }

    // Обновление кнопки "Удалить выбранные"
    function updateDeleteButton() {
        const checked = document.querySelectorAll('.user-checkbox:checked').length;
        btnDeleteSelected.disabled = checked === 0;
    }

    // Выделить все
    selectAll.addEventListener('change', () => {
        document.querySelectorAll('.user-checkbox:not(:disabled)').forEach(cb => {
            cb.checked = selectAll.checked;
        });
        updateDeleteButton();
    });

    // Слушатель чекбоксов
    tableBody.addEventListener('change', updateDeleteButton);

    // Удалить выбранные
    btnDeleteSelected.addEventListener('click', () => {
        const ids = Array.from(document.querySelectorAll('.user-checkbox:checked'))
            .map(cb => cb.dataset.id);

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
            }
        });
    });

    // Удалить все старые неподтверждённые
    btnDeleteOld.addEventListener('click', () => {
        if (!confirm('Удалить ВСЕ неподтверждённые аккаунты старше 24 часов?')) return;

        fetch('/admin/api/users/delete-old-unconfirmed', {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(`Удалено: ${data.deleted_count} пользователей`);
                loadUsers();
            }
        });
    });

    // Первый запуск
    loadUsers();
});