document.addEventListener("DOMContentLoaded", function () {
    // === Элементы основного меню ===
    const accountButton = document.getElementById("account-button");
    const dropdownMenu = document.getElementById("account-menu");
    const cartIcon = document.querySelector('.js-shopping-cart');
    const messBadge = document.getElementById('mess-count-badge');

    let isMainMenuOpen = false;

    // 1. Логика основного меню (аккаунт)
    if (accountButton && dropdownMenu) {
        accountButton.addEventListener("click", function (e) {
            e.preventDefault();
            isMainMenuOpen = !isMainMenuOpen;
            this.setAttribute("aria-expanded", isMainMenuOpen);
            dropdownMenu.style.display = isMainMenuOpen ? "block" : "none";
        });

        dropdownMenu.addEventListener("mouseleave", function () {
            isMainMenuOpen = false;
            accountButton.setAttribute("aria-expanded", false);
            dropdownMenu.style.display = "none";
        });

        document.addEventListener("click", function (e) {
            if (!accountButton.contains(e.target) && !dropdownMenu.contains(e.target)) {
                isMainMenuOpen = false;
                accountButton.setAttribute("aria-expanded", false);
                dropdownMenu.style.display = "none";
            }
        });
    }


    // 2. Логика иконки корзины
    if (cartIcon) {
        cartIcon.addEventListener("click", function () {
            window.location.href = "/user/cart";
        });

        cartIcon.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                window.location.href = "/user/cart";
            }
        });
    }

    // 3. Бэйдж для отображения кол-ва не прочитаных сообщений
    if (!messBadge) return;
    fetch('/api/chat/unread-count', { credentials: 'include' })
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('mess-count-badge');
            if (!badge) return;

            if (data.unread_count > 0) {
                badge.textContent = '+' + data.unread_count; // ← плюсик здесь
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        })
        .catch(err => {
            console.warn('Не удалось загрузить статус сообщений:', err);
            const badge = document.getElementById('mess-count-badge');
            if (badge) badge.style.display = 'none';
        });

});