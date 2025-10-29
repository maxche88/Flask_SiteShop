// ===============================
// AJAX: Добавляет товар в корзину
// ===============================
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

// ==================================
// Функция: "Купить сейчас"
// ==================================
function buyNow(productId) {
    // Дополнительная проверка на валидность ID
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
