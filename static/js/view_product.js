document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('ask-about-product-modal');
    const openBtn = document.getElementById('open-ask-modal-btn');
    const closeBtn = document.getElementById('close-ask-modal');
    const form = document.getElementById('ask-about-product-form');

    if (!modal || !openBtn || !form) return;

    // Получаем данные из глобальных переменных (установлены в шаблоне)
    const userRole = window.userRole || 'guest';
    const productId = window.product_id || '';

    // Устанавливаем product_id в скрытое поле формы (если есть)
    const productIdInput = form.querySelector('[name="product_id"]');
    if (productIdInput && productId) {
        productIdInput.value = productId;
    }

    // Открытие модального окна
    openBtn.addEventListener('click', () => {
        modal.classList.remove('hidden');
    });

    // Закрытие по кнопке
    closeBtn?.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    // Закрытие по клику вне контента
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });

    // Отправка формы
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const messageInput = form.querySelector('[name="message"]');
        const message = messageInput?.value.trim() || '';

        if (!message) {
            showNotification('Введите сообщение.');
            return;
        }

        // Определяем, какие данные собирать
        let payload = {
            text: message,
            product_id: productId,
            context: 'product_question'
        };

        // Для гостей: собираем имя и email
        if (userRole === 'guest') {
            const nameInput = form.querySelector('[name="name"]');
            const emailInput = form.querySelector('[name="email"]');

            const name = nameInput?.value.trim() || '';
            const email = emailInput?.value.trim() || '';

            if (!name) {
                showNotification('Введите имя.');
                return;
            }
            if (!email) {
                showNotification('Введите email.');
                return;
            }

            payload.guest_name = name;
            payload.guest_email = email;
        }

        // Определяем URL эндпоинта
        let url;
        if (userRole === 'guest') {
            url = '/api/chat/dialogs/guest';
        } else if (userRole === 'user') {
            url = '/api/chat/dialogs/user';
        } else {
            // suser, admin и другие — запрещено
            showNotification('У вас нет прав для отправки вопросов о товаре.');
            return;
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const res = await response.json();

            if (response.ok) {
                showNotification('Ваш вопрос отправлен!');
                modal.classList.add('hidden');
                form.reset();
            } else {
                const errorMsg = res.errors?.join('\n') || res.message || 'Не удалось отправить вопрос';
                showNotification('Ошибка: ' + errorMsg);
            }
        } catch (err) {
            console.error('Ошибка сети:', err);
            showNotification('Ошибка подключения к серверу.');
        }
    });
});