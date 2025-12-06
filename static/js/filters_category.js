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

    // --- Переключение видимости расширенных фильтров с закрытием гостевого окна ---
    filtersToggle?.addEventListener('click', (e) => {
        e.stopPropagation();
        // Закрыть гостевое окно, если открыто
        const guestWrapper = document.getElementById('guest-contact-wrapper');
        if (guestWrapper && guestWrapper.classList.contains('expanded')) {
            guestWrapper.classList.remove('expanded');
        }
        advancedFilters.classList.toggle('advanced_filters--visible');
    });

    // --- Закрытие фильтров по клику вне ---
    document.addEventListener('click', function (e) {
        if (advancedFilters.classList.contains('advanced_filters--visible') &&
            e.target !== filtersToggle &&
            !advancedFilters.contains(e.target)) {
            advancedFilters.classList.remove('advanced_filters--visible');
        }
    });

    // --- Очистка всех фильтров ---
    clearFiltersBtn?.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        if (priceMinInput) priceMinInput.value = '';
        if (priceMaxInput) priceMaxInput.value = '';
        if (saleCheckbox) saleCheckbox.checked = false;
        if (sortSelect) sortSelect.value = '';

        categoryCheckboxes.forEach(cb => cb.checked = false);

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

    // --- Обновление активных фильтров ---
    function updateActiveFilters() {
        const selectedCategories = Array.from(categoryCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        const title = searchInput?.value.trim() || '';
        const price_min = parseInputNumber('price_min');
        const price_max = parseInputNumber('price_max');
        const sale = saleCheckbox?.checked || false;
        const sort = sortSelect?.value || '';

        appliedFilters = {
            categories: selectedCategories.length ? selectedCategories : null,
            title: title,
            price_min: price_min,
            price_max: price_max,
            sale: sale,
            sort: sort
        };

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
            if (label) labels.push(label);
        }

        activeFilters.textContent = labels.join(', ');
    }

    // --- Парсинг чисел из input ---
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
            if (appliedFilters.categories) {
                appliedFilters.categories.forEach(cat => params.append('category', cat));
            }
            if (appliedFilters.title) params.append('title', appliedFilters.title);
            if (appliedFilters.price_min !== undefined) params.append('price_min', appliedFilters.price_min);
            if (appliedFilters.price_max !== undefined) params.append('price_max', appliedFilters.price_max);
            if (appliedFilters.sale) params.append('sale', appliedFilters.sale);
            if (appliedFilters.sort) params.append('sort', appliedFilters.sort);
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

                img.src = `${product.img_url}`;
                img.alt = product.title;
                articleNum.textContent = `Артикул: ${product.article_num}`;
                titleLink.textContent = product.title;
                titleLink.href = `/product/${product.id}`;
                price.textContent = `${product.price} ₽`;
                description.textContent = truncateText(product.description, 100);
                badge.style.display = product.sale ? 'flex' : 'none';

                // === Обработка кнопок в зависимости от наличия ===
                const blockBuy = clone.querySelector('.block_buy');
                if (blockBuy) {
                    const userActions = document.createElement('div');
                    userActions.className = 'user-actions';

                    if (product.quantity <= 0) {
                        // Нет в наличии — показываем текст
                        const outOfStock = document.createElement('div');
                        outOfStock.className = 'out-of-stock';
                        outOfStock.textContent = 'Нет в наличии';
                        userActions.appendChild(outOfStock);
                        userActions.style.display = 'block'; // всегда виден
                    } else {
                        // Есть в наличии — кнопки для авторизованных
                        const buyBtn = document.createElement('div');
                        buyBtn.className = 'btn_buy';
                        buyBtn.dataset.productId = product.id;
                        buyBtn.innerHTML = '<div class="btn_text">Купить</div>';

                        const cartLink = document.createElement('a');
                        cartLink.href = '#';
                        cartLink.className = 'cart-icon';
                        cartLink.title = 'Добавить в корзину';
                        cartLink.dataset.productId = product.id;
                        cartLink.innerHTML = `
                        <svg class="img_c icon icon--cart-add-mini" width="25" height="25" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
                        <circle cx="7" cy="22" r="2"/>
                        <circle cx="17" cy="22" r="2"/>
                        <path d="M19.75,13.162A2.5,2.5,0,0,1,17.339,15H7.217a.329.329,0,0,1-.325-.3L6.036,8H10.5A1.5,1.5,0,0,0,12,6.5h0A1.5,1.5,0,0,0,10.5,5H5.653L5.391,2.939A3.327,3.327,0,0,0,2.087,0H1.5a1.5,1.5,0,0,0,0,3h.587a.329.329,0,0,1,.325.3l1.5,11.76A3.327,3.327,0,0,0,7.217,18H17.339a5.5,5.5,0,0,0,5.3-4.042l.016-.06A1.5,1.5,0,0,0,21.213,12h0a1.5,1.5,0,0,0-1.446,1.1Z"/>
                        <path d="M22.5,3H21V1.5a1.5,1.5,0,0,0-3,0V3H16.5a1.5,1.5,0,0,0,0,3H18V7.5a1.5,1.5,0,0,0,3,0V6h1.5a1.5,1.5,0,0,0,0-3Z"/>
                        </svg>
                        `;

                        userActions.appendChild(buyBtn);
                        userActions.appendChild(cartLink);
                        userActions.style.display = (window.userRole === 'user') ? '' : 'none';
                    }

                    blockBuy.appendChild(userActions);
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