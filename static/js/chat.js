document.addEventListener('DOMContentLoaded', function () {
    const wrapper = document.getElementById('guest-contact-wrapper');
    if (!wrapper) return;

    const tab = wrapper.querySelector('.guest-contact-tab');
    const closeBtn = document.getElementById('close-guest-modal');
    const form = document.getElementById('guest-contact-form');
    const categorySelect = document.getElementById('guest-category');

    let topicsLoaded = false;

    // === Загрузка категорий ===
    async function loadTopics() {
        if (topicsLoaded || !categorySelect) return;

        try {
            const response = await fetch('/api/chat/topics');
            if (!response.ok) throw new Error('Сеть ответила с ошибкой');

            const topics = await response.json();

            // Очистка селекта
            categorySelect.innerHTML = '';

            // Плейсхолдер
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.text = '— Выберите категорию —';
            placeholder.disabled = true;
            placeholder.selected = true;
            categorySelect.appendChild(placeholder);

            // Добавление тем
            topics.forEach(topic => {
                const option = document.createElement('option');
                option.value = topic.id;
                option.textContent = topic.name;
                categorySelect.appendChild(option);
            });

            topicsLoaded = true;
        } catch (error) {
            console.error('Ошибка загрузки категорий:', error);
            categorySelect.innerHTML = '<option value="">— Ошибка загрузки —</option>';
        }
    }

    // === Управление окном ===
    function closeWindow() {
        wrapper.classList.remove('expanded');
    }

    function openWindow() {
        // Закрыть фильтры
        const filters = document.getElementById('advanced-filters');
        if (filters) {
            filters.classList.remove('advanced_filters--visible');
        }

        // Загрузить темы и открыть
        if (!topicsLoaded) {
            loadTopics().then(() => {
                wrapper.classList.add('expanded');
            });
        } else {
            wrapper.classList.add('expanded');
        }
    }

    // Обработчики открытия/закрытия
    tab?.addEventListener('click', function () {
        if (wrapper.classList.contains('expanded')) {
            closeWindow();
        } else {
            openWindow();
        }
    });

    closeBtn?.addEventListener('click', closeWindow);

    // Закрытие по клику вне
    document.addEventListener('click', function (e) {
        if (wrapper.classList.contains('expanded') &&
            !wrapper.contains(e.target) &&
            !e.target.closest('.guest-contact-tab')) {
            closeWindow();
        }
    });

    // === Отправка формы ===
    if (form) {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();

            const name = document.getElementById('guest-name')?.value.trim();
            const email = document.getElementById('guest-email')?.value.trim();
            const category = document.getElementById('guest-category')?.value;
            const message = document.getElementById('guest-message')?.value.trim();

            if (!name || !email || !category || !message) {
                alert('Пожалуйста, заполните все поля.');
                return;
            }

            const payload = {
                guest_name: name,
                guest_email: email,
                topic_id: parseInt(category, 10),
                text: message
            };

            try {
                const response = await fetch('/api/chat/guest-dialogs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();

                if (result.success) {
                    alert(result.message);
                    form.reset();
                    closeWindow();
                } else {
                    alert('Ошибка: ' + (result.errors?.[0] || 'Неизвестная ошибка'));
                }
            } catch (err) {
                console.error('Ошибка отправки:', err);
                alert('Не удалось отправить сообщение. Проверьте подключение.');
            }
        });
    }
});