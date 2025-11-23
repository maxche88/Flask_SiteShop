document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('ask-about-product-modal');
    const openBtn = document.getElementById('open-ask-modal-btn');
    const closeBtn = document.getElementById('close-ask-modal');
    const form = document.getElementById('ask-about-product-form');

    if (!modal || !openBtn || !form) return;

    openBtn.addEventListener('click', () => {
        modal.classList.remove('hidden');
    });

    closeBtn?.addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const isGuest = form.querySelector('[name="name"]') !== null;
        const message = form.querySelector('[name="message"]')?.value.trim() || '';
        const productId = form.querySelector('[name="product_id"]')?.value || '';

        if (!message) {
            alert('Введите сообщение.');
            return;
        }

        let payload = {
            text: message,
            product_id: productId,
            context: 'product_question'
        };

        if (isGuest) {
            const name = form.querySelector('[name="name"]')?.value.trim() || '';
            const email = form.querySelector('[name="email"]')?.value.trim() || '';

            if (!name) {
                alert('Введите имя.');
                return;
            }
            if (!email) {
                alert('Введите email.');
                return;
            }

            payload.guest_name = name;
            payload.guest_email = email;
        }

        try {
            const response = await fetch('/api/chat/dialogs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const res = await response.json();
            if (response.ok) {
                alert('Ваш вопрос отправлен!');
                modal.classList.add('hidden');
                form.reset();
            } else {
                alert('Ошибка: ' + (res.errors?.[0] || res.message || 'Не удалось отправить'));
            }
        } catch (err) {
            console.error('Ошибка:', err);
            alert('Ошибка подключения');
        }
    });
});