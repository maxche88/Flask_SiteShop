// Логика страницы корзины

document.addEventListener("DOMContentLoaded", function () {
    // 1. Удаление товаров из корзины
    document.querySelectorAll(".delete-btn").forEach((btn) => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();

            const itemId = this.getAttribute("data-id");

            // Проверка ID
            if (!itemId || isNaN(itemId)) {
                alert("Неверный ID товара для удаления");
                return;
            }

            // Подтверждение удаления
            if (!confirm("Вы уверены, что хотите удалить этот товар?")) {
                return;
            }

            // Отправка запроса на удаление
            fetch(`/api/user/cart?item_id=${itemId}`, {
                method: "DELETE",
                credentials: 'include'
            })
            .then(response => {
                if (response.ok) {
                    // Удаляем строку <tr> из таблицы
                    const row = this.closest('tr');
                    if (row) {
                        row.remove();

                        // Проверим, не стала ли корзина пустой
                        const tableBody = document.querySelector('#cart-table-body');
                        if (tableBody && tableBody.children.length === 0) {
                            const cartTable = document.getElementById('cart-table');
                            if (cartTable) {
                                const emptyMessage = document.createElement('p');
                                emptyMessage.className = 'cart_empty';
                                emptyMessage.textContent = 'Корзина пуста';
                                cartTable.replaceWith(emptyMessage);
                            }

                            // Скрыть кнопку "Оформить заказ"
                            const checkoutBtn = document.getElementById('checkout-button');
                            if (checkoutBtn) {
                                const btnOrder = checkoutBtn.closest('.btn_order');
                                if (btnOrder) btnOrder.remove();
                            }
                        }
                    } else {
                        location.reload(); // fallback
                    }
                } else {
                    return response.json().catch(() => ({}))
                        .then(json => {
                            const message = json.error || 'Неизвестная ошибка';
                            throw new Error(message);
                        });
                }
            })
            .catch(error => {
                console.error("Ошибка при удалении:", error);
                alert("Не удалось удалить товар: " + error.message);
            });
        });
    });

    // 2. Кнопка "Оформить заказ" — пока заглушка
    const checkoutButton = document.getElementById("checkout-button");
    if (checkoutButton) {
        checkoutButton.addEventListener("click", function (e) {
            e.preventDefault();
            alert("Данная функция находится в разработке!");
        });
    }
});