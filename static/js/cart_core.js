//Ядро корзины
// Функции корзины — работают на ЛЮБОЙ странице

function addToCart(productId) {
    const formData = new FormData();
    formData.append("product_id", productId);
    formData.append("quantity", 1);

    return fetch("/user/cart", {
        method: "POST",
        body: formData,
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                throw new Error(`Ошибка ${response.status}: ${text}`);
            });
        }
        return response.json();
    });
}

function buyNow(productId) {
    if (!productId || productId <= 0) {
        console.error("Некорректный ID товара:", productId);
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
            console.error("Ошибка:", error);
            alert("Ошибка: " + error.message);
        });
}

// Универсальный обработчик и управление видимостью
document.addEventListener('DOMContentLoaded', function () {
    const userRole = window.userRole || '';

    // === Управление видимостью кнопок ===
    const userActions = document.querySelectorAll('.user-actions');
    if (userRole === 'user') {
        // Показываем все блоки .user-actions
        userActions.forEach(el => {
            el.style.display = ''; // сбрасываем inline-стиль
        });
    } else {
        // Скрываем все блоки .user-actions
        userActions.forEach(el => {
            el.style.display = 'none';
        });
    }

    // === Обработчик для кнопки "Купить" ===
    document.addEventListener('click', function (e) {
        const buyBtn = e.target.closest('.btn_buy');
        if (buyBtn) {
            e.preventDefault();
            if (userRole !== 'user') return;

            const id = buyBtn.dataset.productId;
            if (id && !isNaN(id) && parseInt(id) > 0) {
                buyNow(parseInt(id));
            } else {
                console.error("Некорректный ID товара:", id);
                alert("Не удалось определить товар для покупки.");
            }
        }
    });

    // === Обработчик для иконки корзины ===
    document.addEventListener('click', function (e) {
        const cartIcon = e.target.closest('.cart-icon');
        if (cartIcon) {
            e.preventDefault();
            if (userRole !== 'user') return;

            const id = cartIcon.dataset.productId;
            if (id && !isNaN(id) && parseInt(id) > 0) {
                addToCart(parseInt(id));
            } else {
                console.error("Не найден ID товара для корзины");
                alert("Не удалось добавить товар.");
            }
        }
    });
});