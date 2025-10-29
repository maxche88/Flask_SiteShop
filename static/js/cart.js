document.addEventListener("DOMContentLoaded", function () {
    // 1. Удаление товаров из корзины
    document.querySelectorAll(".delete-btn").forEach((btn) => {
        btn.addEventListener("click", function () {
            const itemId = this.getAttribute("data-id");

            fetch(`/user/cart?item_id=${itemId}`, {
                method: "DELETE",
            }).then(() => {
                location.reload(); // Перезагружаем страницу после удаления
            }).catch(error => {
                console.error("Ошибка при удалении:", error);
                alert("Не удалось удалить товар");
            });
        });
    });

    // 2. Заглушка для кнопки "Оформить заказ"
    const checkoutButton = document.getElementById("checkout-button");
    if (checkoutButton) {
        checkoutButton.addEventListener("click", function (e) {
            e.preventDefault(); // Предотвращаем переход по ссылке (если это <a>)
            alert("Данная функция находится в разработке!");
        });
    }
});