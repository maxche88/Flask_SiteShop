document.addEventListener("DOMContentLoaded", function () {
    // === 1. Элементы DOM ===
    const articleInput = document.getElementById("article-number");
    const nameInput = document.getElementById("product-name");
    const descriptionInput = document.getElementById("product-description");
    const priceInput = document.getElementById("product-price");
    const saleCheckbox = document.getElementById("product-sale");

    const previewArticle = document.getElementById("preview-article");
    const previewTitle = document.querySelector(".title_product a");
    const previewDescription = document.getElementById("preview-description");
    const previewPrice = document.getElementById("preview-price");
    const badge = document.querySelector(".badge");

    // === Checkbox для переключения превью ===
    const togglePreviewCheckbox = document.getElementById("toggle-preview");
    const previewWrapper = document.getElementById("product-card-preview-wrapper");

    // === 2. Аккордеон категории ===
    const customSelect = document.getElementById('category-select');
    const categoryInput = document.getElementById('product-category');
    const optionsContainer = document.getElementById('category-options');
    const selectHeader = customSelect ? customSelect.querySelector('.select-header') : null;

    // === 3. Логика аккордеона ===
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

    // === 4. Функция обновления превью ===
    function updatePreview() {
        previewArticle.textContent = articleInput?.value || "—";
        previewTitle.textContent = nameInput?.value || "Товар";
        previewDescription.textContent = descriptionInput?.value || "Описание отсутствует";
        
        const price = parseFloat(priceInput?.value);
        previewPrice.textContent = !isNaN(price) ? `${price.toLocaleString('ru-RU')} ₽` : "—";

        badge.style.display = saleCheckbox?.checked ? "inline-block" : "none";
    }

    // === 5. Слушатели ввода ===
    [articleInput, nameInput, descriptionInput, priceInput, saleCheckbox].forEach(input => {
        if (input) {
            input.addEventListener("input", updatePreview);
        }
    });

    // === Управление видимостью превью ===
    if (togglePreviewCheckbox && previewWrapper) {
        // Скрываем превью при загрузке страницы
        previewWrapper.style.display = 'none';
        togglePreviewCheckbox.checked = false; // убедимся, что чекбокс выключен

        togglePreviewCheckbox.addEventListener('change', function () {
            previewWrapper.style.display = this.checked ? 'block' : 'none';
        });
    }

    // === 6. Инициализация превью ===
    updatePreview();

    // === 7. Отправка формы ===
    const form = document.getElementById('productForm');
    if (!form) return;

    // Получаем ID товара из data-атрибута — надёжно и без парсинга URL
    const productId = form.dataset.productId;
    if (!productId) {
        console.error('Не указан data-product-id в форме. Редактирование невозможно.');
        return;
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const formData = new FormData(form);

        try {
            const response = await fetch(`/api/products/${productId}`, {
                method: 'PUT',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                // Успешное обновление — возврат
                if (document.referrer && document.referrer.startsWith(window.location.origin)) {
                    window.location.href = document.referrer;
                } else {
                    window.location.href = '/panel/suser-panel';
                }
            } else {
                const errorMsg = result.error || `Ошибка ${response.status}`;
                alert(`Не удалось обновить товар: ${errorMsg}`);
            }
        } catch (error) {
            console.error('Ошибка сети при отправке формы:', error);
            alert('Ошибка подключения к серверу. Проверьте соединение.');
        }
    });
});