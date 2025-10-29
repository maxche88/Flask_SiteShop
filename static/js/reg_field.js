// Проверка совпадения паролей
function checkPasswordsMatch() {
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirm_password").value;
    const errorServer = document.getElementById("errorMessages");
    const icon = document.getElementById("passwordCheckIcon");

    // Не показываем ошибку, если хотя бы одно поле пустое
    if (!password || !confirmPassword) {
        errorServer.innerHTML = "";  // Не показываем ошибку
        if (icon) icon.style.display = "none";
        return;
    }

    // Проверяем совпадение
    if (password === confirmPassword) {
        if (icon) icon.style.display = "inline";
        errorServer.innerHTML = ""; // Очищаем ошибку
    } else {
        if (icon) icon.style.display = "none";
        errorServer.innerHTML = "<div>Пароли не совпадают</div>";
    }
}

// Слушатель на ввод в поля паролей
document.getElementById("password").addEventListener("input", checkPasswordsMatch);
document.getElementById("confirm_password").addEventListener("input", checkPasswordsMatch);

// Обработка отправки формы
document.getElementById("registerForm").addEventListener("submit", function(e) {
    e.preventDefault();

    // Элементы
    const errorServer = document.getElementById("errorMessages");
    const submitBtn = document.getElementById("submitBtn");

    // Очистка предыдущих ошибок
    errorServer.innerHTML = "";

    // Блокируем кнопку
    submitBtn.disabled = true;
    submitBtn.textContent = "Загрузка...";

    // Сбор данных
    const formData = {
        username: document.getElementById("username").value,
        email: document.getElementById("email").value,
        password: document.getElementById("password").value,
        confirm_password: document.getElementById("confirm_password").value
    };

    // Отправка запроса
    fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
    })
    .then(response => {
        return response.json().then(data => {
            if (data.success) {
                // Успех: показываем сообщение и перенаправляем
                errorServer.style.color = "green";
                errorServer.textContent = data.message || "Успешно!";
                setTimeout(() => {
                    window.location.href = "/login"; // Перенаправление на login
                }, 1000); // Задержка для лучшего UX
            } else {
                // Ошибки: выводим в интерфейс
                errorServer.style.color = "red";
                if (data.errors && Array.isArray(data.errors)) {
                    errorServer.innerHTML = data.errors.map(err => `<div>${err}</div>`).join('');
                } else {
                    errorServer.textContent = "Произошла неизвестная ошибка.";
                }
            }
        });
    })
    .catch(err => {
        errorServer.style.color = "red";
        errorServer.textContent = "Не удалось подключиться к серверу.";
        console.error(err);
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = "Отправить";
    });
});