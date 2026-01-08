/**
 * Модуль управления интерфейсом личного кабинета пользователя.
 * Инициализирует обработчики для редактирования имени, email и смены пароля.
 * Использует данные, переданные из шаблона через скрытый JSON-элемент.
 */
(function () {
    // === Извлечение данных, переданных из бэкенда ===
    const PROFILE_DATA = JSON.parse(document.getElementById('profile-data').textContent);
    const globalNotification = document.getElementById('globalNotification');

    // === Вспомогательная функция: отображение временного уведомления ===
    function showNotification(element, message, isSuccess) {
        if (!element) return;

        element.textContent = message;
        element.style.display = "block";
        element.style.backgroundColor = isSuccess ? "#e8f5e9" : "#ffebee";
        element.style.color = isSuccess ? "#2e7d32" : "#c62828";
        element.style.border = isSuccess ? "1px solid #a5d6a7" : "1px solid #ffcdd2";

        setTimeout(() => {
            element.style.display = "none";
        }, 5000);
    }

    // === === === БЛОК: СМЕНА ПАРОЛЯ === === ===
    const changePasswordButton = document.getElementById('changePasswordBtn');
    if (changePasswordButton) {
        changePasswordButton.addEventListener('click', async function () {
            const userEmail = PROFILE_DATA.email;

            // Подтверждение
            if (!confirm(`Отправить ссылку для смены пароля на ваш email:\n${userEmail}?`)) {
                return;
            }

            const originalTitle = this.title;
            this.disabled = true;
            this.title = "Отправка...";

            try {
                const response = await fetch("/reset-password", {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: `email=${encodeURIComponent(userEmail)}`
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

                showNotification(globalNotification, message, isSuccess);
            } catch (err) {
                console.error("Ошибка сети при сбросе пароля:", err);
                showNotification(globalNotification, "Ошибка подключения. Попробуйте позже.", false);
            } finally {
                this.disabled = false;
                this.title = originalTitle;
            }
        });
    }

    // === === === БЛОК: РЕДАКТИРОВАНИЕ ИМЕНИ === === ===
    const editUsernameButton = document.querySelector('[data-field="username"]');
    const usernameEditForm = document.getElementById('usernameEditView');
    const newUsernameInput = document.getElementById('newUsernameInput');
    const submitUsernameButton = document.getElementById('submitUsernameBtn');
    const cancelUsernameButton = document.getElementById('cancelUsernameBtn');

    if (editUsernameButton && usernameEditForm) {
        editUsernameButton.addEventListener('click', () => {
            newUsernameInput.value = PROFILE_DATA.username || '';
            usernameEditForm.style.display = 'flex';
            newUsernameInput.focus();
            newUsernameInput.select();
        });
    }

    if (cancelUsernameButton) {
        cancelUsernameButton.addEventListener('click', () => {
            usernameEditForm.style.display = 'none';
            newUsernameInput.value = '';
        });
    }

    if (submitUsernameButton) {
        submitUsernameButton.addEventListener('click', async () => {
            const rawValue = newUsernameInput.value.trim();
            const currentName = PROFILE_DATA.username;

            if (!rawValue) {
                showNotification(globalNotification, "Имя не может быть пустым.", false);
                return;
            }
            if (rawValue === currentName) {
                showNotification(globalNotification, "Это текущее имя.", false);
                return;
            }
            if (rawValue.length < 2) {
                showNotification(globalNotification, "Имя должно содержать минимум 2 символа.", false);
                return;
            }

            const originalText = submitUsernameButton.textContent;
            submitUsernameButton.disabled = true;
            submitUsernameButton.textContent = "Сохранение…";

            try {
                const response = await fetch("/api/user/update-username", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: rawValue })
                });

                const result = await response.json();

                if (result.success) {
                    document.querySelector('[data-editable="username"]').textContent = result.username;
                    PROFILE_DATA.username = result.username;
                    usernameEditForm.style.display = 'none';
                    newUsernameInput.value = '';
                    showNotification(globalNotification, "Имя успешно изменено!", true);
                } else {
                    showNotification(globalNotification, result.error || "Ошибка при изменении имени.", false);
                }
            } catch (err) {
                console.error("Ошибка сети при изменении имени:", err);
                showNotification(globalNotification, "Не удалось подключиться к серверу.", false);
            } finally {
                submitUsernameButton.disabled = false;
                submitUsernameButton.textContent = originalText;
            }
        });
    }

    // === === === БЛОК: РЕДАКТИРОВАНИЕ EMAIL === === ===
    const editEmailButton = document.getElementById('editEmailBtn');
    const emailStaticView = document.getElementById('emailStaticView');
    const pendingEmailView = document.getElementById('pendingEmailView');
    const emailEditForm = document.getElementById('emailEditView');
    const newEmailInput = document.getElementById('newEmailInput');
    const submitEmailButton = document.getElementById('submitEmailBtn');
    const cancelEmailButton = document.getElementById('cancelEmailBtn');
    const delPEmailButton = document.getElementById('delPEmailBtn');

    function updateEditEmailButtonState() {
        if (!editEmailButton) return;
        const isPending = Boolean(PROFILE_DATA.pending_email);
        editEmailButton.disabled = isPending;
        editEmailButton.style.opacity = isPending ? '0.5' : '0.7';
        editEmailButton.style.pointerEvents = isPending ? 'none' : 'auto';
        editEmailButton.title = isPending
            ? 'Нельзя изменить: ожидается подтверждение email'
            : 'Изменить email';
    }

    // Инициализация
    if (PROFILE_DATA.pending_email && pendingEmailView) {
        pendingEmailView.style.display = 'flex';
        const valueEl = pendingEmailView.querySelector('.profile-pending-email-value');
        if (valueEl) valueEl.textContent = PROFILE_DATA.pending_email;
    } else if (pendingEmailView) {
        pendingEmailView.style.display = 'none';
    }
    updateEditEmailButtonState();

    if (editEmailButton && emailEditForm) {
        editEmailButton.addEventListener('click', () => {
            if (PROFILE_DATA.pending_email) {
                // НЕОБХОДИМО ИЗМЕНИТЬ
                showNotification(`На ${PROFILE_DATA.pending_email} вам была отправлена ссылка для подтверждения, перейдите по ней.`);
                return;
            }
            newEmailInput.value = '';
            emailEditForm.style.display = 'flex';
            newEmailInput.focus();
        });
    }

    if (cancelEmailButton) {
        cancelEmailButton.addEventListener('click', () => {
            emailEditForm.style.display = 'none';
            newEmailInput.value = '';
        });
    }

    if (submitEmailButton) {
        submitEmailButton.addEventListener('click', async () => {
            const rawValue = newEmailInput.value.trim();
            const currentEmail = PROFILE_DATA.email;

            if (!rawValue) {
                showNotification(globalNotification, "Email не может быть пустым.", false);
                return;
            }
            if (rawValue === currentEmail) {
                showNotification(globalNotification, "Это текущий email.", false);
                return;
            }
            if (!rawValue.includes('@')) {
                showNotification(globalNotification, "Введите корректный email (должен содержать @).", false);
                return;
            }

            const originalText = submitEmailButton.textContent;
            submitEmailButton.disabled = true;
            submitEmailButton.textContent = "Отправка…";

            try {
                const response = await fetch("/change-email-request", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: rawValue })
                });

                const result = await response.json();

                if (result.success) {
                    PROFILE_DATA.pending_email = rawValue;

                    if (pendingEmailView) {
                        pendingEmailView.style.display = 'flex';
                        const valueEl = pendingEmailView.querySelector('.profile-pending-email-value');
                        if (valueEl) valueEl.textContent = rawValue;
                    }

                    emailEditForm.style.display = 'none';
                    newEmailInput.value = '';
                    updateEditEmailButtonState();
                    showNotification(globalNotification, result.message, true);
                } else {
                    showNotification(globalNotification, result.errors?.[0] || "Ошибка при отправке запроса.", false);
                }
            } catch (err) {
                console.error("Ошибка при отправке email:", err);
                showNotification(globalNotification, "Не удалось отправить запрос.", false);
            } finally {
                submitEmailButton.disabled = false;
                submitEmailButton.textContent = originalText;
            }
        });
    }

    // --- Удаление неподтверждённого email ---
    if (delPEmailButton) {
        delPEmailButton.addEventListener('click', async () => {
            if (!PROFILE_DATA.pending_email) {
                // НЕОБХОДИМО ИЗМЕНИТЬ
                showNotification("Нет активного запроса на смену email.");
                return;
            }

            // Подтверждение остаётся
            if (!confirm(`Отменить запрос на смену email на ${PROFILE_DATA.pending_email}?`)) {
                return;
            }

            const originalTitle = delPEmailButton.title;
            delPEmailButton.disabled = true;
            delPEmailButton.title = "Отмена...";

            try {
                const response = await fetch("/cancel-email-change", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" }
                });

                const result = await response.json();

                if (result.success) {
                    PROFILE_DATA.pending_email = null;
                    if (pendingEmailView) {
                        pendingEmailView.style.display = 'none';
                    }
                    updateEditEmailButtonState();
                    showNotification(globalNotification, result.message, true);
                } else {
                    showNotification(globalNotification, result.error || "Не удалось отменить запрос.", false);
                }
            } catch (err) {
                console.error("Ошибка при отмене email:", err);
                showNotification(globalNotification, "Ошибка подключения.", false);
            } finally {
                delPEmailButton.disabled = false;
                delPEmailButton.title = originalTitle;
            }
        });
    }
})();