// Обработчик формы
document.getElementById("loginForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const errorServer = document.getElementById("errorMessages");
    const submitBtn = document.getElementById("submitBtn");

    errorServer.innerHTML = "";
    submitBtn.disabled = true;
    submitBtn.textContent = "Загрузка...";

    const formData = {
        username: document.getElementById("username").value,
        password: document.getElementById("password").value
    };

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            const data = await response.json();
            if (data.errors && data.errors.length > 0) {
                errorServer.style.color = "red";
                errorServer.textContent = data.errors[0];
            } else {
                errorServer.textContent = "Ошибка авторизации.";
            }
        } else {
            const data = await response.json();
            if (data.success) {
                // Извлекаем токен из ответа и ставим его в cookie
                document.cookie = `access_token=${data.access_token}; path=/; SameSite=Lax`;
                
                // Выполняем редирект на главную страницу
                window.location.href = "/";
            }
        }
    } catch (err) {
        errorServer.style.color = "red";
        errorServer.textContent = "Не удалось подключиться к серверу.";
        console.error("Ошибка входа:", err);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Войти";
    }
});