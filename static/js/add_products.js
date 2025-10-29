document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('productForm');
    if (!form) return;

    const categorySelect = document.getElementById('category-select');
    const selectHeader = categorySelect?.querySelector('.select-header');
    const selectOptions = categorySelect?.querySelector('.select-options');
    const categoryInput = document.getElementById('product-category');
    const fileInput = document.getElementById('product-image');
    const fileNameDisplay = document.getElementById('file-name');
    const errorMessages = document.getElementById('errorMessages');

    let isCategoryOpen = false;

    // === Логика кастомного селекта: открытие/закрытие ===
    if (selectHeader && selectOptions) {
        selectHeader.addEventListener('click', function () {
            if (isCategoryOpen) {
                selectOptions.style.display = 'none';
                categorySelect.classList.remove('open');
            } else {
                selectOptions.style.display = 'block';
                categorySelect.classList.add('open');
            }
            isCategoryOpen = !isCategoryOpen;
        });

        // Закрытие при клике вне селекта
        document.addEventListener('click', function (e) {
            if (categorySelect && !categorySelect.contains(e.target)) {
                selectOptions.style.display = 'none';
                categorySelect.classList.remove('open');
                isCategoryOpen = false;
            }
        });
    }

    // === Выбор категории из списка ===
    const categoryOptions = selectOptions?.querySelectorAll('li');
    if (categoryOptions && categoryInput && selectHeader) {
        categoryOptions.forEach(option => {
            option.addEventListener('click', function () {
                const value = this.getAttribute('data-value');
                const text = this.textContent;

                categoryInput.value = value;
                selectHeader.textContent = text;

                // Закрываем список
                if (selectOptions) {
                    selectOptions.style.display = 'none';
                    categorySelect?.classList.remove('open');
                    isCategoryOpen = false;
                }
            });
        });
    }

    // === Обновление имени файла ===
    if (fileInput && fileNameDisplay) {
        fileInput.addEventListener('change', function () {
            if (this.files.length > 0) {
                fileNameDisplay.textContent = this.files[0].name;
            } else {
                fileNameDisplay.textContent = 'Фото не выбрано';
            }
        });
    }

    // === Отправка формы ===
    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        // Очистка предыдущих сообщений
        if (errorMessages) errorMessages.innerHTML = '';

        // Валидация категории
        if (!categoryInput?.value.trim()) {
            showError('Выберите категорию');
            return;
        }

        // Валидация файла
        if (!fileInput || fileInput.files.length === 0) {
            showError('Выберите изображение для товара');
            return;
        }

        // Сбор данных
        const formData = new FormData(form);
        formData.set('category', categoryInput.value.trim());

        // Отправка
        try {
            const response = await fetch('/api/products', {
                method: 'POST',
                body: formData // автоматически устанавливает правильный Content-Type с boundary
            });

            const result = await response.json(); // Ожидается, что сервер вернёт JSON

            if (response.ok) {
                showSuccess('Товар успешно добавлен!');
                form.reset();
                if (fileNameDisplay) fileNameDisplay.textContent = 'Фото не выбрано';
                if (categoryInput) categoryInput.value = '';
                if (selectHeader) selectHeader.textContent = 'Выберите категорию';

                // Автоочистка сообщения через 5 сек
                setTimeout(() => {
                    if (errorMessages) errorMessages.innerHTML = '';
                }, 5000);
            } else {
                const msg = result.error || 'Неизвестная ошибка при добавлении товара';
                showError(msg);
            }
        } catch (err) {
            console.error('Сетевая ошибка:', err);
            showError('Ошибка сети. Проверьте подключение и попробуйте снова.');
        }
    });

    // === Вспомогательные функции ===
    function showError(message) {
        if (errorMessages) {
            errorMessages.innerHTML = `<div class="error-message">❌ ${message}</div>`;
        }
        console.error('Ошибка формы:', message);
    }

    function showSuccess(message) {
        if (errorMessages) {
            errorMessages.innerHTML = `<div class="success-message">✅ ${message}</div>`;
        }
        console.log('Успех:', message);
    }
});