document.addEventListener("DOMContentLoaded", function () {
    // === Элементы основного меню ===
    const accountButton = document.getElementById("account-button");
    const dropdownMenu = document.getElementById("account-menu");
    const cartIcon = document.getElementById("shopping-cart");


    let isMainMenuOpen = false;

    // =============================
    // 1. Логика основного меню (аккаунт)
    // =============================
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

    // =============================
    // 2. Логика иконки корзины
    // =============================
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
});