document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('productForm');
    if (!form) return;

    // === Элементы превью ===
    const togglePreviewCheckbox = document.getElementById("toggle-preview");
    const previewWrapper = document.getElementById("product-card-preview-wrapper");

    const previewArticle = document.getElementById("preview-article");
    const previewTitle = document.getElementById("preview-title-link");
    const previewDescription = document.getElementById("preview-description");
    const previewPrice = document.getElementById("preview-price");
    const badge = document.querySelector(".badge-preview");
    const previewImage = document.getElementById("preview-image");

    // === Поля формы ===
    const articleInput = document.getElementById("article-number");
    const nameInput = document.getElementById("product-name");
    const descriptionInput = document.getElementById("product-description");
    const priceInput = document.getElementById("product-price");
    const saleCheckbox = document.getElementById("product-sale");

    // === Функция обновления превью ===
    function updatePreview() {
        if (previewArticle) previewArticle.textContent = articleInput?.value || "—";
        if (previewTitle) previewTitle.textContent = nameInput?.value || "Товар";
        if (previewDescription) previewDescription.textContent = descriptionInput?.value || "Описание отсутствует";

        let priceValue = priceInput?.value?.trim() || '';
        let price = NaN;
        if (priceValue !== '') {
            priceValue = priceValue.replace(',', '.');
            price = parseFloat(priceValue);
        }
        if (previewPrice) {
            previewPrice.textContent = !isNaN(price) ? `${price.toLocaleString('ru-RU')} ₽` : "—";
        }

        if (badge) {
            if (saleCheckbox?.checked) {
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
    }

    // === Слушатели ввода ===
    [articleInput, nameInput, descriptionInput, priceInput, saleCheckbox].forEach(input => {
        if (input) {
            input.addEventListener("input", updatePreview);
        }
    });

    // === Управление превью ===
    if (togglePreviewCheckbox && previewWrapper) {
        togglePreviewCheckbox.checked = false;
        previewWrapper.style.display = 'none';

        togglePreviewCheckbox.addEventListener('change', function () {
            previewWrapper.style.display = this.checked ? 'block' : 'none';
        });
    }

    // === Категория ===
    const categorySelect = document.getElementById('category-select');
    const selectHeader = categorySelect?.querySelector('.select-header');
    const selectOptions = categorySelect?.querySelector('.select-options');
    const categoryInput = document.getElementById('product-category');

    let isCategoryOpen = false;
    if (selectHeader && selectOptions) {
        selectHeader.addEventListener('click', () => {
            isCategoryOpen = !isCategoryOpen;
            selectOptions.style.display = isCategoryOpen ? 'block' : 'none';
            categorySelect?.classList.toggle('open', isCategoryOpen);
        });

        document.addEventListener('click', (e) => {
            if (categorySelect && !categorySelect.contains(e.target)) {
                selectOptions.style.display = 'none';
                categorySelect?.classList.remove('open');
                isCategoryOpen = false;
            }
        });

        const options = selectOptions?.querySelectorAll('li');
        if (options && categoryInput && selectHeader) {
            options.forEach(li => {
                li.addEventListener('click', () => {
                    const value = li.dataset.value;
                    selectHeader.textContent = value;
                    categoryInput.value = value;
                    selectOptions.style.display = 'none';
                    categorySelect?.classList.remove('open');
                    isCategoryOpen = false;
                    updatePreview();
                });
            });
        }
    }

    // === Изображение ===
    const fileInput = document.getElementById('product-image');
    const fileNameDisplay = document.getElementById('file-name');

    if (fileInput && fileNameDisplay) {
        fileInput.addEventListener('change', function () {
            const file = this.files[0];
            if (file) {
                fileNameDisplay.textContent = '✅ Новое фото товара загружено';
                fileNameDisplay.className = 'file-name success';

                if (previewImage && togglePreviewCheckbox?.checked) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        previewImage.src = e.target.result;
                    };
                    reader.readAsDataURL(file);
                }
            } else {
                fileNameDisplay.textContent = 'Фото не выбрано';
                fileNameDisplay.className = 'file-name';
                if (previewImage) previewImage.src = '';
            }
        });
    }

    // === Отправка ===
    const errorMessages = document.getElementById('errorMessages');
    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        if (errorMessages) errorMessages.innerHTML = '';

        if (!categoryInput?.value.trim()) {
            showError('Выберите категорию');
            return;
        }
        if (!fileInput || fileInput.files.length === 0) {
            showError('Выберите изображение');
            return;
        }

        const formData = new FormData(form);
        formData.set('category', categoryInput.value.trim());

        try {
            const response = await fetch('/api/products', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            if (response.ok) {
                showSuccess('Товар добавлен!');
                form.reset();
                if (fileNameDisplay) fileNameDisplay.textContent = 'Фото не выбрано';
                if (categoryInput) categoryInput.value = '';
                if (selectHeader) selectHeader.textContent = 'Выберите категорию';
                if (previewImage) previewImage.src = '';
                if (badge) badge.classList.add('hidden');
                updatePreview(); // сброс превью
            } else {
                showError(result.error || 'Ошибка сервера');
            }
        } catch (err) {
            showError('Ошибка сети');
        }
    });

    // === Вспомогательные функции ===
    function showError(msg) {
        if (errorMessages) errorMessages.innerHTML = `<div class="error-message">❌ ${msg}</div>`;
    }
    function showSuccess(msg) {
        if (errorMessages) errorMessages.innerHTML = `<div class="success-message">✅ ${msg}</div>`;
    }

    // === Инициализация ===
    updatePreview();
});