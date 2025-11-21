document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('ask-about-product-modal');
    const closeBtn = document.getElementById('close-ask-modal');
    const form = document.getElementById('ask-about-product-form');
    const productTitleSpan = document.getElementById('modal-product-title');
    const productIdInput = document.getElementById('modal-product-id');

    if (!modal || !form) return;

    function openModal(productId, productTitle) {
        if (productTitleSpan) productTitleSpan.textContent = productTitle || 'товар';
        if (productIdInput) productIdInput.value = productId;
    }

    function closeModal() {
        modal.classList.add('hidden');
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const message = form.querySelector('[name="message"]')?.value.trim();
        const productId = productIdInput?.value;

        if (!message) return alert('Введите сообщение.');
        if (!productId) return alert('Не указан товар.');

        try {
            const res = await fetch('/api/chat/dialogs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    text: message,
                    product_id: productId,
                    context: 'product_question'
                })
            });

            const data = await res.json();
            if (res.ok) {
                alert('Ваш вопрос отправлен!');
                closeModal();
                form.reset();
            } else {
                alert('Ошибка: ' + (data.message || 'Не удалось отправить'));
            }
        } catch (err) {
            console.error('Ошибка:', err);
            alert('Ошибка подключения');
        }
    });

    // Обработчик клика по иконке чата
    document.querySelectorAll('.cart-icon').forEach(btn => {
        if (!btn.hasAttribute('data-product-id')) return;

        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const productId = this.getAttribute('data-product-id');
            let productTitle = 'товар';

            const row = this.closest('tr');
            if (row) {
                const titleCell = row.querySelector('.product-title');
                if (titleCell) productTitle = titleCell.textContent.trim();
            }

            openModal(productId, productTitle);
        });
    });
});