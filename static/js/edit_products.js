document.addEventListener("DOMContentLoaded", function () {
    // === 1. Элементы DOM ===
    const articleInput = document.getElementById("article-number");
    const nameInput = document.getElementById("product-name");
    const descriptionInput = document.getElementById("product-description");
    const priceInput = document.getElementById("product-price");
    const saleCheckbox = document.getElementById("product-sale");

    const previewArticle = document.getElementById("preview-article");
    const previewTitle = document.getElementById("preview-title-link");
    const previewDescription = document.getElementById("preview-description");
    const previewPrice = document.getElementById("preview-price");
    const badge = document.querySelector(".badge-preview");

    // === Checkbox для переключения превью ===
    const togglePreviewCheckbox = document.getElementById("toggle-preview");
    const previewWrapper = document.getElementById("product-card-preview-wrapper");

    // === 2. Аккордеон категории ===
    const customSelect = document.getElementById('category-select');
    const categoryInput = document.getElementById('product-category');
    const optionsContainer = document.getElementById('category-options');
    const selectHeader = customSelect ? customSelect.querySelector('.select-header') : null;

    if (customSelect && selectHeader && optionsContainer) {
        selectHeader.addEventListener('click', () => {
            optionsContainer.classList.toggle('show');
            selectHeader.classList.toggle('active');
        });

        optionsContainer.addEventListener('click', (e) => {
            if (e.target.matches('li')) {
                const value = e.target.dataset.value;
                selectHeader.textContent = value;
                categoryInput.value = value;
                updatePreview();
                optionsContainer.classList.remove('show');
                selectHeader.classList.remove('active');
            }
        });

        document.addEventListener('click', (e) => {
            if (!customSelect.contains(e.target)) {
                optionsContainer.classList.remove('show');
                selectHeader.classList.remove('active');
            }
        });
    }

    // === Функция обновления превью ===
    function updatePreview() {
        if (previewArticle) previewArticle.textContent = articleInput?.value || "—";
        if (previewTitle) previewTitle.textContent = nameInput?.value || "Товар";
        if (previewDescription) previewDescription.textContent = descriptionInput?.value || "Описание отсутствует";
        
        const price = parseFloat(priceInput?.value);
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

    // === Подключаем live-обновление ===
    [articleInput, nameInput, descriptionInput, priceInput, saleCheckbox].forEach(input => {
        if (input) {
            input.addEventListener("input", updatePreview);
        }
    });

    // === Инициализация (заполнение превью начальными данными) ===
    updatePreview();

    // === 5. Слушатели ввода ===
    [articleInput, nameInput, descriptionInput, priceInput, saleCheckbox].forEach(input => {
        if (input) {
            input.addEventListener("input", updatePreview);
        }
    });

    // === Управление видимостью превью ===
    if (togglePreviewCheckbox && previewWrapper) {
        previewWrapper.style.display = 'none';
        togglePreviewCheckbox.checked = false;

        togglePreviewCheckbox.addEventListener('change', function () {
            previewWrapper.style.display = this.checked ? 'block' : 'none';
        });
    }

    // === 6. Обработка изображения ===
    const fileInput = document.getElementById('product-image');
    const fileNameSpan = document.getElementById('file-name');
    const previewImage = document.getElementById('preview-image');

    if (fileInput && fileNameSpan && previewImage) {
        // Получаем исходный путь из data-атрибута
        const originalImagePath = previewImage.dataset.originalSrc || '';
        const originalFilename = originalImagePath ? originalImagePath.substring(originalImagePath.lastIndexOf('/') + 1) || 'изображение.jpg' : 'изображение.jpg';

        function updateFileStatus(isNew = false) {
            if (isNew) {
                fileNameSpan.textContent = '✅ Новое фото товара загружено';
                fileNameSpan.className = 'file-name success';
            } else {
                fileNameSpan.textContent = originalFilename;
                fileNameSpan.className = 'file-name success';
            }
        }

        // Инициализация
        updateFileStatus(false);

        fileInput.addEventListener('change', function () {
            const file = this.files[0];
            if (file) {
                updateFileStatus(true);
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImage.src = e.target.result;
                };
                reader.readAsDataURL(file);
            } else {
                // Отмена — возврат к исходному
                previewImage.src = "/static" + originalImagePath;
                updateFileStatus(false);
            }
        });
    }

    // === 7. Инициализация превью ===
    updatePreview();

    // === 8. Отправка формы ===
    const form = document.getElementById('productForm');
    if (!form) return;

    const productId = form.dataset.productId;
    if (!productId) {
        console.error('Не указан data-product-id в форме. Редактирование невозможно.');
        return;
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const formData = new FormData(form);

        fetch(`/api/products/${productId}`, {
            method: 'PUT',
            body: formData
        })
        .then(response => response.json())
        .then(result => {
            if (result.success || response.ok) {
                if (document.referrer && document.referrer.startsWith(window.location.origin)) {
                    window.location.href = document.referrer;
                } else {
                    window.location.href = '/panel/suser-panel';
                }
            } else {
                alert(`Не удалось обновить товар: ${result.error || 'неизвестная ошибка'}`);
            }
        })
        .catch(error => {
            console.error('Ошибка сети:', error);
            alert('Ошибка подключения к серверу.');
        });
    });
});