// Общий функционал корзины для всех страниц: кнопки, API, управление видимостью

/**
 * Запрашивает текущее количество товаров в корзине и обновляет бейдж
 */
function updateCartBadge() {
    const badge = document.getElementById('cart-count-badge');
    if (!badge) return;

    fetch('/api/user/cart/count', {
        method: 'GET',
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    })
    .then(data => {
        const count = data.count || 0;
        if (count > 0) {
            badge.textContent = '+' + count;
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
    })
    .catch(error => {
        console.warn('Не удалось обновить счётчик корзины:', error);
        badge.style.display = 'none';
    });
}

/**
 * Добавляет товар в корзину через AJAX
 * @param {number} productId — ID товара
 * @returns {Promise<Object>} — ответ от сервера
 */
function addToCart(productId) {
    const formData = new FormData();
    formData.append("product_id", productId);
    formData.append("quantity", 1);

    return fetch("/api/user/cart", {
        method: "POST",
        body: formData,
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().catch(() => ({})) 
                .then(json => {
                    const message = json.error || json.message || 'Неизвестная ошибка';
                    throw new Error(`Ошибка ${response.status}: ${message}`);
                });
        }
        return response.json();
    });
}

/**
 * Добавляет товар и перенаправляет в корзину
 * @param {number} productId
 */
function buyNow(productId) {
    if (!productId || productId <= 0 || isNaN(productId)) {
        console.error("Некорректный ID товара:", productId);
        alert("Невозможно купить товар: неверный ID.");
        return;
    }

    addToCart(productId)
        .then(data => {
            if (data.success) {
                window.location.href = "/user/cart"; 
            } else {
                alert("Ошибка при добавлении товара");
            }
        })
        .catch(error => {
            console.error("Ошибка при покупке:", error);
            alert("Ошибка: " + (error.message || "Неизвестная ошибка"));
        });
}

// === Инициализация при загрузке DOM ===
document.addEventListener('DOMContentLoaded', function () {
    const userRole = window.userRole || '';

    // Управление видимостью блоков для авторизованных пользователей
    const userActions = document.querySelectorAll('.user-actions');
    if (userRole === 'user') {
        userActions.forEach(el => {
            el.style.display = '';
        });

        updateCartBadge();
    } else {
        userActions.forEach(el => {
            el.style.display = 'none';
        });
    }

    // Обработчик кнопок "Купить сейчас"
    document.addEventListener('click', function (e) {
        const buyBtn = e.target.closest('.btn_buy');
        if (buyBtn) {
            e.preventDefault();
            if (userRole !== 'user') {
                alert("Только для авторизованных пользователей");
                return;
            }

            const id = buyBtn.dataset.productId;
            const productId = parseInt(id, 10);
            if (id && !isNaN(productId) && productId > 0) {
                buyNow(productId);
            } else {
                console.error("Некорректный ID товара:", id);
                alert("Не удалось определить товар для покупки.");
            }
        }
    });

    // Обработчик иконок "Добавить в корзину"
    document.addEventListener('click', function (e) {
        const cartIcon = e.target.closest('.cart-icon');
        if (cartIcon) {
            e.preventDefault();
            if (userRole !== 'user') {
                alert("Только для авторизованных пользователей");
                return;
            }

            const id = cartIcon.dataset.productId;
            const productId = parseInt(id, 10);
            if (id && !isNaN(productId) && productId > 0) {
                addToCart(productId)
                    .then(data => {
                        if (data.success) {
                            updateCartBadge();
                            console.log("Товар добавлен в корзину");
                        } else {
                            alert("Не удалось добавить товар");
                        }
                    })
                    .catch(error => {
                        console.error("Ошибка при добавлении:", error);
                        alert("Ошибка: " + (error.message || "Неизвестная ошибка"));
                    });
            } else {
                console.error("Не найден ID товара");
                alert("Не удалось добавить товар.");
            }
        }
    });
});