// Функция для проверки совпадения паролей
function checkPasswordsMatch() {
    const password = document.getElementById("password")?.value || '';
    const confirmPassword = document.getElementById("confirm_password")?.value || '';
    const errorServer = document.getElementById("errorMessages");
    const icon = document.getElementById("passwordCheckIcon");

    // Если одно из полей пустое — скрываем ошибку и иконку
    if (!password || !confirmPassword) {
        if (errorServer) errorServer.textContent = "";
        if (icon) icon.style.display = "none";
        return;
    }

    if (password === confirmPassword) {
        if (icon) icon.style.display = "inline";
        if (errorServer) errorServer.textContent = "";
    } else {
        if (icon) icon.style.display = "none";
        if (errorServer) errorServer.textContent = "Пароли не совпадают";
    }
}

// Добавляем обработчики только если элементы существуют
const passwordInput = document.getElementById("password");
const confirmPasswordInput = document.getElementById("confirm_password");

if (passwordInput) passwordInput.addEventListener("input", checkPasswordsMatch);
if (confirmPasswordInput) confirmPasswordInput.addEventListener("input", checkPasswordsMatch);

window.addEventListener("load", checkPasswordsMatch);

// Обработка отправки формы
const form = document.getElementById("setNewPasswordForm");
if (form) {
    form.addEventListener("submit", function(e) {
        e.preventDefault();

        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get("token");
        const errorServer = document.getElementById("errorMessages");
        const submitBtn = document.getElementById("submitBtn");

        // Сброс ошибок
        if (errorServer) {
            errorServer.textContent = "";
            errorServer.style.display = "none";
        }

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = "Сохранение...";
        }

        const password = document.getElementById("password")?.value || '';
        const confirm_password = document.getElementById("confirm_password")?.value || '';

        // Клиентская валидация
        if (!password || !confirm_password) {
            if (errorServer) {
                errorServer.textContent = "Пароль не может быть пустым";
                errorServer.style.display = "block";
            }
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = "Сохранить пароль";
            }
            return;
        }

        if (password !== confirm_password) {
            if (errorServer) {
                errorServer.textContent = "Пароли не совпадают";
                errorServer.style.display = "block";
            }
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = "Сохранить пароль";
            }
            return;
        }

        // Отправка JSON-запроса на универсальный роутер
        fetch(`/reset-password/token?token=${encodeURIComponent(token)}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                password: password,
                confirm_password: confirm_password
            })
        })
        .then(response => {
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                return response.json().then(data => {
                    if (response.ok) {
                        // Успех — редирект или сообщение
                        window.location.href = "/auth/login?reset_success=1";
                    } else {
                        // Ошибка от API
                        throw new Error(data.error || "Неизвестная ошибка");
                    }
                });
            } else {
                // Сервер вернул HTML (например, при ошибке валидации без JSON)
                return response.text().then(html => {
                    throw new Error("Сервер вернул HTML вместо JSON. Убедитесь, что роут поддерживает JSON.");
                });
            }
        })
        .catch(error => {
            console.error("Ошибка при сбросе пароля:", error);
            if (errorServer) {
                errorServer.textContent = error.message || "Не удалось подключиться к серверу";
                errorServer.style.display = "block";
            }
        })
        .finally(() => {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = "Сохранить пароль";
            }
        });
    });
}