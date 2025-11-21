document.addEventListener("DOMContentLoaded", function () {
    // Функция пересчёта итогов
    function updateCartSummary() {
        let totalItems = 0;
        let totalPrice = 0;

        document.querySelectorAll('#cart-table-body tr').forEach(row => {
            const checkbox = row.querySelector('.item-checkbox');
            if (checkbox && checkbox.checked) {
                const quantityInput = row.querySelector('.qty-input');
                const priceCell = row.querySelector('td:nth-child(3)');

                const quantity = parseInt(quantityInput.value) || 0;
                const priceText = priceCell.textContent.trim();
                const price = parseInt(priceText.replace(/[^0-9]/g, '')) || 0;

                totalItems += quantity;
                totalPrice += price * quantity;
            }
        });

        const totalItemsEl = document.getElementById('total-items');
        const totalPriceEl = document.getElementById('total-price');
        if (totalItemsEl) totalItemsEl.textContent = totalItems;
        if (totalPriceEl) totalPriceEl.textContent = totalPrice;
    }

    // Вспомогательные функции для оплаты
    function formatCardNumber(value) {
        const digits = value.replace(/\D/g, '');
        const formatted = digits.match(/.{1,4}/g)?.join(' ') || '';
        return formatted;
    }

    function validateExpiry(expiry) {
        const match = expiry.match(/^(\d{2})\/(\d{2})$/);
        if (!match) return false;

        const month = parseInt(match[1], 10);
        const year = parseInt(match[2], 10);
        if (month < 1 || month > 12) return false;

        const now = new Date();
        const currentYear = now.getFullYear() % 100;
        const currentMonth = now.getMonth() + 1;

        if (year < currentYear) return false;
        if (year === currentYear && month < currentMonth) return false;

        return true;
    }

    // Инициализация чекбоксов
    document.querySelectorAll('.item-checkbox').forEach(cb => {
        cb.checked = true;
    });

    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.addEventListener('change', function () {
            const isChecked = this.checked;
            document.querySelectorAll('.item-checkbox').forEach(cb => cb.checked = isChecked);
            updateCartSummary();
        });
    }

    document.querySelectorAll('.item-checkbox').forEach(cb => {
        cb.addEventListener('change', function () {
            if (selectAllCheckbox) {
                const allChecked = Array.from(document.querySelectorAll('.item-checkbox')).every(cb => cb.checked);
                selectAllCheckbox.checked = allChecked;
            }
            updateCartSummary();
        });
    });

    // Ограничение количества по остатку на складе
    document.querySelectorAll('.qty-input').forEach(input => {
        const max = parseInt(input.getAttribute('data-stock')) || 1;
        const min = 1;
        input.setAttribute('max', max);

        input.addEventListener('input', function () {
            let value = parseInt(this.value) || min;
            if (value < min) value = min;
            if (value > max) value = max;
            this.value = value;
            updateCartSummary();
        });

        input.addEventListener('paste', function () {
            setTimeout(() => {
                let value = parseInt(this.value) || min;
                if (value < min || value > max) {
                    this.value = Math.min(max, Math.max(min, value));
                }
                updateCartSummary();
            }, 10);
        });
    });

    // Удаление товаров
    document.querySelectorAll(".cart-delete-icon").forEach((btn) => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const itemId = this.getAttribute("data-id");
            if (!itemId || itemId === '#') {
                if (itemId !== '#') alert("Неверный ID товара");
                return;
            }

            if (!confirm("Вы уверены, что хотите удалить этот товар?")) return;

            fetch(`/api/user/cart?item_id=${itemId}`, {
                method: "DELETE",
                credentials: 'include'
            })
            .then(response => {
                if (response.ok) {
                    const row = this.closest('tr');
                    if (row) row.remove();

                    if (document.querySelectorAll('#cart-table-body tr').length === 0) {
                        const table = document.getElementById('cart-table');
                        if (table) {
                            const msg = document.createElement('p');
                            msg.className = 'cart_empty';
                            msg.textContent = 'Корзина пуста';
                            table.replaceWith(msg);
                        }
                        document.querySelector('.btn_order')?.remove();
                        document.getElementById('cart-summary')?.remove();
                    }
                    updateCartSummary();
                } else {
                    return response.json().then(json => {
                        throw new Error(json.error || 'Ошибка сервера');
                    });
                }
            })
            .catch(error => {
                console.error("Ошибка при удалении:", error);
                alert("Не удалось удалить: " + error.message);
            });
        });
    });

    // Модальное окно оплаты
    const checkoutButton = document.getElementById("checkout-button");
    const modal = document.getElementById("payment-modal");
    const closeModal = document.querySelector(".close");
    const paymentForm = document.getElementById("payment-form");

    if (checkoutButton) {
        checkoutButton.addEventListener("click", function (e) {
            e.preventDefault();
            const totalPrice = parseInt(document.getElementById('total-price').textContent);
            if (totalPrice <= 0) {
                alert("Выберите хотя бы один товар.");
                return;
            }
            document.getElementById('modal-total-price').textContent = totalPrice + ' ₽';
            document.getElementById('btn-amount').textContent = totalPrice + ' ₽';
            modal.style.display = "block";
        });
    }

    if (closeModal) {
        closeModal.addEventListener("click", () => modal.style.display = "none");
    }
    window.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
    });

    // Отправка формы оплаты
    if (paymentForm) {
        const cardNumberInput = document.getElementById("card-number");
        cardNumberInput.addEventListener("input", function (e) {
            e.target.value = formatCardNumber(e.target.value);
        });

        paymentForm.addEventListener("submit", function (e) {
            e.preventDefault();

            const cardNumber = document.getElementById("card-number").value.replace(/\s/g, '');
            const cardholderName = document.getElementById("cardholder-name").value.trim();
            const expiry = document.getElementById("expiry").value.trim();

            const selectedItems = [];
            document.querySelectorAll('.item-checkbox:checked').forEach(cb => {
                const row = cb.closest('tr');
                const itemId = cb.value;
                const qtyInput = row.querySelector('.qty-input');
                const quantity = parseInt(qtyInput.value) || 1;
                selectedItems.push({ item_id: parseInt(itemId), quantity: quantity });
            });

            if (cardNumber.length !== 16 || !/^\d{16}$/.test(cardNumber)) {
                alert("Номер карты должен содержать 16 цифр");
                return;
            }
            if (!cardholderName) {
                alert("Введите имя владельца");
                return;
            }
            if (!validateExpiry(expiry)) {
                alert("Укажите корректный срок действия (ММ/ГГ)");
                return;
            }
            if (selectedItems.length === 0) {
                alert("Нет выбранных товаров");
                return;
            }

            fetch("/api/user/checkout", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({
                    items: selectedItems,
                    card_number: cardNumber,
                    cardholder_name: cardholderName,
                    expiry: expiry
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert("Заказ успешно оформлен!");
                    modal.style.display = "none";
                    window.location.reload();
                } else {
                    let errorMsg = data.error || "Неизвестная ошибка";
                    if (data.details && Array.isArray(data.details)) {
                        errorMsg += "\n\n" + data.details.join("\n");
                    }
                    alert("Ошибка: " + errorMsg);
                }
            })
                    .catch(err => {
                        console.error("Ошибка сети:", err);
                        alert("Не удалось отправить заказ.");
                    });
                });
            }

    // Модальное окно: задать вопрос о товаре из корзины
    const askModal = document.querySelector('.cart-ask-overlay');
    const askForm = document.querySelector('.cart-ask-form');
    const askTitleSpan = document.querySelector('.cart-ask-product-title');
    const askProductIdInput = document.querySelector('.cart-ask-product-id');
    const askCloseBtn = document.querySelector('.cart-ask-close');

    if (askModal && askForm) {
        document.querySelectorAll('.cart-send_mess-icon').forEach(btn => {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                const row = this.closest('tr');
                const productId = this.getAttribute('data-product-id');
                const productTitle = row.querySelector('td:nth-child(2)')?.textContent?.trim() || 'Неизвестный товар';
                askTitleSpan.textContent = productTitle;
                askProductIdInput.value = productId;
                askModal.classList.remove('hidden');
            });
        });

        if (askCloseBtn) {
            askCloseBtn.addEventListener('click', () => {
                askModal.classList.add('hidden');
                askForm.reset();
            });
        }

        askModal.addEventListener('click', (e) => {
            if (e.target === askModal) {
                askModal.classList.add('hidden');
                askForm.reset();
            }
        });

        askForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const message = askForm.querySelector('[name="message"]')?.value.trim() || '';
            const productId = askForm.querySelector('[name="product_id"]')?.value || '';

            if (!message) {
                alert('Введите ваш вопрос.');
                return;
            }
            if (!productId) {
                alert('Не удалось определить товар.');
                return;
            }

            const payload = {
                text: message,
                product_id: productId,
                context: 'product_question'
            };

            try {
                const response = await fetch('/api/chat/dialogs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(payload)
                });

                const res = await response.json();
                if (response.ok) {
                    alert('Ваш вопрос отправлен!');
                    askModal.classList.add('hidden');
                    askForm.reset();
                } else {
                    alert('Ошибка: ' + (res.errors?.[0] || res.message || 'Не удалось отправить вопрос'));
                }
            } catch (err) {
                console.error('Ошибка при отправке вопроса:', err);
                alert('Не удалось отправить вопрос. Попробуйте позже.');
            }
        });
    }

    // Инициализация
    updateCartSummary();
});