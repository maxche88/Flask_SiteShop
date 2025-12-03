(function () {
    const PROFILE_DATA = JSON.parse(document.getElementById('profile-data').textContent);

    // === Смена пароля ===
    const changePasswordBtn = document.getElementById('changePasswordBtn');
    if (changePasswordBtn) {
        changePasswordBtn.addEventListener('click', async function () {
            const { email } = PROFILE_DATA;
            if (!confirm(`Отправить ссылку для смены пароля на ваш email:\n${email}?`)) return;

            const btn = this;
            const notificationEl = document.getElementById('passwordNotification');
            btn.disabled = true;
            btn.title = "Отправка...";

            try {
                const response = await fetch("/reset-password", {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: `email=${encodeURIComponent(email)}`
                });

                const html = await response.text();
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, "text/html");
                const errorEl = doc.querySelector('.err');
                const successEl = doc.querySelector('.mess');

                let message = "Неизвестный результат.";
                let isSuccess = false;
                if (successEl) {
                    message = successEl.textContent.trim();
                    isSuccess = true;
                } else if (errorEl) {
                    message = errorEl.textContent.trim();
                    isSuccess = false;
                }

                showNotification(notificationEl, message, isSuccess);
            } catch (err) {
                console.error("Ошибка сети:", err);
                showNotification(notificationEl, "Ошибка подключения. Попробуйте позже.", false);
            } finally {
                btn.disabled = false;
                btn.title = "Сменить пароль";
            }
        });
    }

    // === Редактирование имени ===
    const editUsernameBtn = document.querySelector('[data-field="username"]');
    if (editUsernameBtn) {
        editUsernameBtn.addEventListener('click', function () {
            const newValue = prompt("Введите новое имя:", PROFILE_DATA.username);
            if (newValue && newValue !== PROFILE_DATA.username && newValue.trim().length >= 2) {
                updateField('username', newValue.trim(), (updated) => {
                    document.querySelector('[data-editable="username"]').textContent = updated;
                    PROFILE_DATA.username = updated;
                });
            }
        });
    }

    // === Редактирование email: инлайн-форма ===
    const editEmailBtn = document.getElementById('editEmailBtn');
    const emailStaticView = document.getElementById('emailStaticView');
    const emailEditView = document.getElementById('emailEditView');
    const newEmailInput = document.getElementById('newEmailInput');
    const submitEmailBtn = document.getElementById('submitEmailBtn');
    const cancelEmailBtn = document.getElementById('cancelEmailBtn');

    if (editEmailBtn && emailStaticView && emailEditView) {
        editEmailBtn.addEventListener('click', () => {
            if (PROFILE_DATA.pending_email) {
                alert(`На ${PROFILE_DATA.pending_email} вам была отправлена ссылка для подтверждения, перейтите по ней.`);
                return;
            }

            // Показываем форму редактирования
            emailStaticView.style.display = 'none';
            emailEditView.style.display = 'flex';
            newEmailInput.value = PROFILE_DATA.email;
            newEmailInput.focus();
            newEmailInput.select();
        });
    }

    if (cancelEmailBtn) {
        cancelEmailBtn.addEventListener('click', () => {
            emailStaticView.style.display = 'flex';
            emailEditView.style.display = 'none';
        });
    }

    if (submitEmailBtn) {
        submitEmailBtn.addEventListener('click', async () => {
            const newEmail = newEmailInput.value.trim();
            if (!newEmail || newEmail === PROFILE_DATA.email || !newEmail.includes('@')) {
                alert("Введите корректный новый email.");
                return;
            }

            const btn = submitEmailBtn;
            const originalText = btn.textContent;
            const notificationEl = document.getElementById('emailNotification');

            btn.disabled = true;
            btn.textContent = "Отправка...";

            try {
                const response = await fetch("/change-email-request", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: newEmail })
                });

                const data = await response.json();

                if (data.success) {
                    // Обновляем UI: добавляем бейдж pending_email
                    const badge = document.createElement('span');
                    badge.className = 'status-badge status-warning';
                    badge.title = 'Ожидает подтверждения';
                    badge.textContent = `⏳ ${newEmail}`;

                    const group = document.querySelector('#emailField .field-value-group');
                    const oldBadge = group.querySelector('.status-badge');
                    if (oldBadge) oldBadge.remove();
                    const editBtn = document.getElementById('editEmailBtn');
                    if (editBtn) {
                        group.insertBefore(badge, editBtn);
                    }

                    // Обновляем данные
                    PROFILE_DATA.pending_email = newEmail;

                    // Возвращаемся к просмотру
                    emailStaticView.style.display = 'flex';
                    emailEditView.style.display = 'none';

                    showNotification(notificationEl, data.message, true);
                } else {
                    showNotification(notificationEl, data.errors?.[0] || "Ошибка", false);
                }
            } catch (err) {
                console.error("Ошибка:", err);
                showNotification(notificationEl, "Не удалось отправить запрос", false);
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        });
    }

    // === Вспомогательные функции ===
    function showNotification(el, message, isSuccess) {
        if (!el) return;
        el.textContent = message;
        el.style.display = "block";
        el.style.backgroundColor = isSuccess ? "#e8f5e9" : "#ffebee";
        el.style.color = isSuccess ? "#2e7d32" : "#c62828";
        el.style.border = isSuccess ? "1px solid #a5d6a7" : "1px solid #ffcdd2";
        setTimeout(() => { el.style.display = "none"; }, 5000);
    }

    async function updateField(field, value, onSuccess) {
        const btn = document.querySelector(`[data-field="${field}"]`);
        if (!btn) return;

        try {
            const response = await fetch(`/api/user/update-${field}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ [field]: value })
            });
            const data = await response.json();
            if (data.success && onSuccess) {
                onSuccess(data[field]);
            } else {
                alert("Ошибка: " + (data.error || "неизвестная"));
            }
        } catch (err) {
            alert("Не удалось обновить");
        }
    }
})();