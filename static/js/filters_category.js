// filters_category.js
// Фильтрация товаров с поддержкой множественного выбора категорий через чекбоксы

document.addEventListener('DOMContentLoaded', function () {
    const productContainer = document.getElementById('product-container');
    if (!productContainer) return;

    const searchBtn = document.getElementById('search-btn');
    const filtersToggle = document.getElementById('toggle-filters');
    const advancedFilters = document.getElementById('advanced-filters');
    const clearFiltersBtn = document.getElementById('clear-filters');
    const activeFilters = document.getElementById('active-filters');

    // Получаем все чекбоксы категорий
    const categoryCheckboxes = document.querySelectorAll('input[name="category"]');

    let appliedFilters = {};

    // --- Переключение видимости расширенных фильтров ---
    filtersToggle?.addEventListener('click', () => {
        advancedFilters.classList.toggle('advanced_filters--visible');
    });

    // --- Очистка всех фильтров ---
    clearFiltersBtn?.addEventListener('click', () => {
        // Сбрасываем поля
        document.getElementById('search-input').value = '';
        document.getElementById('price_min').value = '';
        document.getElementById('price_max').value = '';
        document.getElementById('sale_checkbox').checked = false;

        // Сбрасываем чекбоксы категорий
        categoryCheckboxes.forEach(cb => cb.checked = false);

        appliedFilters = {};
        activeFilters.textContent = '';
        loadProducts(1);
    });

    // --- Обработчики чекбоксов категорий ---
    categoryCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateActiveFilters);
    });

    // --- Обработчик чекбокса "Только акции" ---
    document.getElementById('sale_checkbox')?.addEventListener('change', updateActiveFilters);

    // --- Поиск по кнопке и Enter ---
    searchBtn?.addEventListener('click', () => {
        updateActiveFilters();
        loadProducts(1);
    });

    document.getElementById('search-input')?.addEventListener('keypress', e => {
        if (e.key === 'Enter') {
            updateActiveFilters();
            loadProducts(1);
        }
    });

    // --- Обновление активных фильтров ---
    function updateActiveFilters() {
        // Собираем выбранные категории
        const selectedCategories = Array.from(categoryCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        appliedFilters = {
            categories: selectedCategories.length ? selectedCategories : null,
            title: document.getElementById('search-input')?.value.trim(),
            price_min: parseInputNumber('price_min'),
            price_max: parseInputNumber('price_max'),
            sale: document.getElementById('sale_checkbox')?.checked
        };

        // Формируем метки для отображения
        const labels = [];
        if (appliedFilters.categories) {
            labels.push(`Категории: ${appliedFilters.categories.join(', ')}`);
        }
        if (appliedFilters.title) {
            labels.push(`Поиск: ${appliedFilters.title}`);
        }
        if (appliedFilters.price_min !== undefined) {
            labels.push(`Цена от: ${appliedFilters.price_min}`);
        }
        if (appliedFilters.price_max !== undefined) {
            labels.push(`Цена до: ${appliedFilters.price_max}`);
        }
        if (appliedFilters.sale) {
            labels.push('Только акции');
        }

        activeFilters.textContent = labels.join(', ');
    }

    // --- Вспомогательная функция: парсинг чисел ---
    function parseInputNumber(id) {
        const el = document.getElementById(id);
        if (!el) return undefined;
        const value = parseFloat(el.value);
        return isNaN(value) ? undefined : value;
    }

    // --- Обрезка текста ---
    function truncateText(text, maxChars = 100) {
        if (!text) return '';
        if (text.length <= maxChars) return text;
        const truncated = text.substring(0, maxChars);
        const lastSpace = truncated.lastIndexOf(' ');
        const cutIndex = lastSpace > maxChars * 0.7 ? lastSpace : maxChars;
        return truncated.substring(0, cutIndex).trim() + '…';
    }

    // --- Загрузка товаров с фильтрацией ---
    async function loadProducts(page = 1) {
        try {
            const params = new URLSearchParams();

            // Передаём каждую выбранную категорию отдельно
            if (appliedFilters.categories) {
                appliedFilters.categories.forEach(cat => {
                    params.append('category', cat);
                });
            }

            // Остальные фильтры
            if (appliedFilters.title) params.append('title', appliedFilters.title);
            if (appliedFilters.price_min !== undefined) params.append('price_min', appliedFilters.price_min);
            if (appliedFilters.price_max !== undefined) params.append('price_max', appliedFilters.price_max);
            if (appliedFilters.sale) params.append('sale', appliedFilters.sale);

            params.append('page', page);
            params.append('per_page', 100);

            const response = await fetch(`/api/products?${params}`);
            const data = await response.json();

            const template = document.getElementById('product-card-template');
            if (page === 1) productContainer.innerHTML = '';

            if (!data.items?.length) {
                productContainer.innerHTML = '<p>Товаров не найдено.</p>';
                return;
            }

            data.items.forEach(product => {
                const clone = template.content.cloneNode(true);
                const img = clone.querySelector('.img_cont');
                const articleNum = clone.querySelector('.article_num p');
                const titleLink = clone.querySelector('.title_product a');
                const description = clone.querySelector('.description p');
                const price = clone.querySelector('.price_product p');
                const badge = clone.querySelector('.badge');

                img.src = `/static${product.img_url}`;
                img.alt = product.title;
                articleNum.textContent = `Артикул: ${product.article_num}`;
                titleLink.textContent = product.title;
                titleLink.href = `/product/${product.id}`;
                price.textContent = `${product.price} ₽`;
                description.textContent = truncateText(product.description, 100);

                badge.style.display = product.sale ? 'flex' : 'none';

                // === Кнопки корзины ===
                const blockBuy = clone.querySelector('.block_buy');
                if (blockBuy) {
                    const userActions = document.createElement('div');
                    userActions.className = 'user-actions';

                    const buyBtn = document.createElement('div');
                    buyBtn.className = 'btn_buy';
                    buyBtn.dataset.productId = product.id;
                    buyBtn.innerHTML = '<div class="btn_text"></div>Купить';

                    const cartLink = document.createElement('a');
                    cartLink.href = '#';
                    cartLink.className = 'cart-icon';
                    cartLink.title = 'Добавить в корзину';
                    cartLink.dataset.productId = product.id;
                    cartLink.innerHTML = `<img class="img_c" src="/static/img/other/cart-add-mini.svg" alt="В корзину" width="25" height="25">`;

                    userActions.appendChild(buyBtn);
                    userActions.appendChild(cartLink);
                    blockBuy.appendChild(userActions);

                    userActions.style.display = (window.userRole === 'user') ? '' : 'none';
                }

                productContainer.appendChild(clone);
            });

        } catch (error) {
            console.error('Ошибка загрузки товаров:', error);
            productContainer.innerHTML = '<p>Ошибка загрузки данных.</p>';
        }
    }

    // Загружаем товары при старте
    loadProducts(1);
});