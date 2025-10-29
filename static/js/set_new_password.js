// Функция для проверки совпадения паролей
function checkPasswordsMatch() {
    const password = document.getElementById("password")?.value || '';
    const confirmPassword = document.getElementById("confirm_password")?.value || '';
    const errorServer = document.getElementById("errorMessages");
    const icon = document.getElementById("passwordCheckIcon");

    // Если одно из полей пустое — не показываем ошибку или иконку
    if (!password || !confirmPassword) {
        errorServer.innerHTML = "";
        if (icon) icon.style.display = "none";
        return;
    }

    if (password === confirmPassword) {
        if (icon) icon.style.display = "inline";
        errorServer.innerHTML = "";
    } else {
        if (icon) icon.style.display = "none";
        errorServer.innerHTML = "<div>Пароли не совпадают</div>";
    }
}

// Слушатель на ввод
document.getElementById("password").addEventListener("input", checkPasswordsMatch);
document.getElementById("confirm_password").addEventListener("input", checkPasswordsMatch);

// Слушатель на загрузку страницы
window.addEventListener("load", checkPasswordsMatch);

// Обработка отправки формы
document.getElementById("setNewPasswordForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const token = new URLSearchParams(window.location.search).get("token");
    const errorServer = document.getElementById("errorMessages");
    const submitBtn = document.getElementById("submitBtn");

    errorServer.textContent = "";
    errorServer.style.display = "none";
    submitBtn.disabled = true;
    submitBtn.textContent = "Загрузка...";

    const password = document.getElementById("password").value;
    const confirm_password = document.getElementById("confirm_password").value;

    if (password !== confirm_password) {
        errorServer.textContent = "Пароли не совпадают";
        errorServer.style.display = "block";
        submitBtn.disabled = false;
        submitBtn.textContent = "Сохранить пароль";
        return;
    }

    fetch(`/reset-password/token?token=${encodeURIComponent(token)}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            password,
            confirm_password
        })
    })

    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = "Сохранить пароль";
    });
});