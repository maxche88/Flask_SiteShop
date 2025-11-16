// Фильтрация товаров на публичной странице каталога

document.addEventListener('DOMContentLoaded', function () {
    const productContainer = document.getElementById('product-container');
    if (!productContainer) return;

    // DOM-элементы
    const searchBtn = document.getElementById('search-btn');
    const filtersToggle = document.getElementById('toggle-filters');
    const advancedFilters = document.getElementById('advanced-filters');
    const clearFiltersBtn = document.getElementById('clear-filters');
    const activeFilters = document.getElementById('active-filters');
    const sortSelect = document.getElementById('sort-select');
    const searchInput = document.getElementById('search-input');
    const priceMinInput = document.getElementById('price_min');
    const priceMaxInput = document.getElementById('price_max');
    const saleCheckbox = document.getElementById('sale_checkbox');

    // Получаем все чекбоксы категорий
    const categoryCheckboxes = document.querySelectorAll('input[name="category"]');

    // Глобальное хранилище применённых фильтров
    let appliedFilters = {};

    // --- Переключение видимости расширенных фильтров ---
    filtersToggle?.addEventListener('click', () => {
        advancedFilters.classList.toggle('advanced_filters--visible');
    });

    // --- Очистка всех фильтров ---
    clearFiltersBtn?.addEventListener('click', () => {
        // Сброс полей ввода
        if (searchInput) searchInput.value = '';
        if (priceMinInput) priceMinInput.value = '';
        if (priceMaxInput) priceMaxInput.value = '';
        if (saleCheckbox) saleCheckbox.checked = false;
        if (sortSelect) sortSelect.value = '';

        // Сброс чекбоксов категорий
        categoryCheckboxes.forEach(cb => cb.checked = false);

        // Очистка состояния и обновление UI
        appliedFilters = {};
        activeFilters.textContent = '';
        loadProducts(1);
    });

    // --- Обработчики чекбоксов категорий ---
    categoryCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            updateActiveFilters();
            loadProducts(1);
        });
    });

    // --- Обработчик чекбокса "Только акции" ---
    saleCheckbox?.addEventListener('change', () => {
        updateActiveFilters();
        loadProducts(1);
    });

    // --- Обработчик сортировки ---
    sortSelect?.addEventListener('change', () => {
        updateActiveFilters();
        loadProducts(1);
    });

    // --- Поиск по кнопке и Enter ---
    searchBtn?.addEventListener('click', () => {
        updateActiveFilters();
        loadProducts(1);
    });

    searchInput?.addEventListener('keypress', e => {
        if (e.key === 'Enter') {
            updateActiveFilters();
            loadProducts(1);
        }
    });

    // --- Обновление активных фильтров (обновляет appliedFilters и отображает метки) ---
    function updateActiveFilters() {
        // Собираем выбранные категории
        const selectedCategories = Array.from(categoryCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        // Получаем значения полей
        const title = searchInput?.value.trim() || '';
        const price_min = parseInputNumber('price_min');
        const price_max = parseInputNumber('price_max');
        const sale = saleCheckbox?.checked || false;
        const sort = sortSelect?.value || '';

        // Сохраняем в глобальное состояние
        appliedFilters = {
            categories: selectedCategories.length ? selectedCategories : null,
            title: title,
            price_min: price_min,
            price_max: price_max,
            sale: sale,
            sort: sort
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
        if (appliedFilters.sort) {
            const sortLabels = {
                'price_asc': 'Сортировка: Цена ↑',
                'price_desc': 'Сортировка: Цена ↓',
                'created_at_desc': 'Сортировка: Сначала новые',
                'created_at_asc': 'Сортировка: Сначала старые'
            };
            const label = sortLabels[appliedFilters.sort];
            if (label) {
                labels.push(label);
            }
        }

        activeFilters.textContent = labels.join(', ');
    }

    // --- Вспомогательная функция: парсинг чисел из input ---
    function parseInputNumber(id) {
        const el = document.getElementById(id);
        if (!el) return undefined;
        const value = parseFloat(el.value);
        return isNaN(value) ? undefined : value;
    }

    // --- Обрезка текста описания ---
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

            // Фильтр по категориям (множественный)
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
            if (appliedFilters.sort) params.append('sort', appliedFilters.sort); // ← КЛЮЧЕВАЯ СТРОКА

            params.append('page', page);
            params.append('per_page', 100); // Загружаем все на одной странице

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

                // === Кнопки корзины (только для авторизованных покупателей) ===
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

                    // Показываем только для обычных покупателей (user)
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