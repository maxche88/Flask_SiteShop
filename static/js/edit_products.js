document.addEventListener("DOMContentLoaded", function () {
    // === 1. Элементы DOM ===
    const articleInput = document.getElementById("article-number");
    const nameInput = document.getElementById("product-name");
    const descriptionInput = document.getElementById("product-description");
    const priceInput = document.getElementById("product-price");
    const saleCheckbox = document.getElementById("product-sale");
    const fileInput = document.getElementById("product-image");

    const previewArticle = document.getElementById("preview-article");
    const previewTitle = document.getElementById("preview-title-link");
    const previewDescription = document.getElementById("preview-description");
    const previewPrice = document.getElementById("preview-price");
    const badge = document.querySelector(".badge-preview");

    // Элемент для вывода ошибок
    const errorContainer = document.getElementById("form-error-message");
    if (errorContainer) errorContainer.style.display = "none";

    // === Превью изображения ===
    const fileNameSpan = document.getElementById("file-name");
    const previewImage = document.getElementById("preview-image");
    const originalImagePath = previewImage?.dataset.originalSrc || "";
    const originalFilename = originalImagePath
        ? originalImagePath.substring(originalImagePath.lastIndexOf("/") + 1) || "изображение.jpg"
        : "изображение.jpg";

    // === Управление превью ===
    const togglePreviewCheckbox = document.getElementById("toggle-preview");
    const previewWrapper = document.getElementById("product-card-preview-wrapper");

    // === Кастомный селект категории ===
    const customSelect = document.getElementById("category-select");
    const categoryInput = document.getElementById("product-category");
    const optionsContainer = document.getElementById("category-options");
    const selectHeader = customSelect ? customSelect.querySelector(".select-header") : null;

    // === Функция обновления превью карточки ===
    function updatePreview() {
        if (previewArticle) previewArticle.textContent = articleInput?.value || "—";
        if (previewTitle) previewTitle.textContent = nameInput?.value || "Товар";
        if (previewDescription) previewDescription.textContent = descriptionInput?.value || "Описание отсутствует";

        const price = parseFloat(priceInput?.value);
        if (previewPrice) {
            previewPrice.textContent = !isNaN(price) ? `${price.toLocaleString("ru-RU")} ₽` : "—";
        }

        if (badge) {
            badge.classList.toggle("hidden", !saleCheckbox?.checked);
        }
    }

    // === Функция отображения ошибки ===
    function showError(message) {
        if (errorContainer) {
            errorContainer.textContent = message;
            errorContainer.style.display = "block";
        } else {
            alert(message); // fallback
        }
    }

    // === Функция скрытия ошибки ===
    function hideError() {
        if (errorContainer) {
            errorContainer.style.display = "none";
        }
    }

    // === Обновление статуса файла ===
    function updateFileStatus(isNew = false) {
        if (!fileNameSpan) return;

        if (isNew) {
            fileNameSpan.textContent = "✅ Новое фото товара загружено";
            fileNameSpan.className = "file-name success";
        } else {
            fileNameSpan.textContent = originalFilename;
            fileNameSpan.className = "file-name success";
        }
    }

    // === Инициализация ===
    updatePreview();
    if (fileInput && fileNameSpan && previewImage) {
        updateFileStatus(false);
    }

    if (togglePreviewCheckbox && previewWrapper) {
        previewWrapper.style.display = "none";
        togglePreviewCheckbox.checked = false;

        togglePreviewCheckbox.addEventListener("change", function () {
            previewWrapper.style.display = this.checked ? "block" : "none";
        });
    }

    // === Обработка выбора категории ===
    if (customSelect && selectHeader && optionsContainer) {
        selectHeader.addEventListener("click", () => {
            optionsContainer.classList.toggle("show");
            selectHeader.classList.toggle("active");
        });

        optionsContainer.addEventListener("click", (e) => {
            if (e.target.matches("li")) {
                const value = e.target.dataset.value;
                selectHeader.textContent = value;
                categoryInput.value = value;
                updatePreview();
                optionsContainer.classList.remove("show");
                selectHeader.classList.remove("active");
            }
        });

        document.addEventListener("click", (e) => {
            if (!customSelect.contains(e.target)) {
                optionsContainer.classList.remove("show");
                selectHeader.classList.remove("active");
            }
        });
    }

    // === Слушатели полей ввода ===
    [articleInput, nameInput, descriptionInput, priceInput, saleCheckbox].forEach((input) => {
        if (input) {
            input.addEventListener("input", () => {
                hideError();
                updatePreview();
            });
        }
    });

    if (fileInput) {
        fileInput.addEventListener("change", function () {
            hideError();
            const file = this.files[0];
            if (file && previewImage) {
                updateFileStatus(true);
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImage.src = e.target.result;
                };
                reader.readAsDataURL(file);
            } else {
                // Возврат к исходному изображению
                if (previewImage) previewImage.src = "/static" + originalImagePath;
                updateFileStatus(false);
            }
        });
    }

    // === Отправка формы ===
    const form = document.getElementById("productForm");
    if (!form) return;

    const productId = form.dataset.productId;
    if (!productId) {
        console.error("Не указан data-product-id в форме. Редактирование невозможно.");
        return;
    }

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        hideError();

        const formData = new FormData(form);

        try {
            const response = await fetch(`/api/products/${productId}`, {
                method: "PUT",
                body: formData,
            });

            const result = await response.json();

            if (response.ok) {
                // Успешно
                if (document.referrer && document.referrer.startsWith(window.location.origin)) {
                    window.location.href = document.referrer;
                } else {
                    window.location.href = "/panel/suser-panel";
                }
            } else {
                // Сервер вернул ошибку (4xx/5xx + JSON с полем "error")
                const errorMessage = result.error || "Неизвестная ошибка при обновлении товара.";
                showError(errorMessage);
            }
        } catch (error) {
            console.error("Ошибка сети:", error);
            showError("Ошибка подключения к серверу. Проверьте соединение и попробуйте снова.");
        }
    });
});