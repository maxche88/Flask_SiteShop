// filters_category.js
// Только фильтрация и загрузка товаров

document.addEventListener('DOMContentLoaded', function () {
    // Проверяем, есть ли элементы главной страницы
    const productContainer = document.getElementById('product-container');
    if (!productContainer) return; // Если нет — выходим (не главная страница)

    const searchBtn = document.getElementById('search-btn');
    const filtersToggle = document.getElementById('toggle-filters');
    const advancedFilters = document.getElementById('advanced-filters');
    const activeFilters = document.getElementById('active-filters');
    const categoriesMenu = document.getElementById('categories-menu');
    const categoriesButton = document.getElementById('categories-button');
    const clearFiltersBtn = document.getElementById('clear-filters');

    let currentCategory = '';
    let appliedFilters = {};

    // --- Меню категорий ---
    categoriesButton?.addEventListener('click', () => {
        categoriesMenu.style.display = categoriesMenu.style.display === 'block' ? 'none' : 'block';
    });

    categoriesMenu?.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            currentCategory = this.dataset.category || '';
            updateActiveFilters();
            categoriesMenu.style.display = 'none';
        });
    });

    // --- Фильтры ---
    filtersToggle?.addEventListener('click', () => {
        advancedFilters.classList.toggle('advanced_filters--visible');
    });

    clearFiltersBtn?.addEventListener('click', () => {
        document.getElementById('price_min').value = '';
        document.getElementById('price_max').value = '';
        document.getElementById('sale_checkbox').checked = false;
        currentCategory = '';
        appliedFilters = {};
        activeFilters.innerHTML = '';
        loadProducts(1);
    });

    function updateActiveFilters() {
        appliedFilters = {
            category: currentCategory,
            title: document.getElementById('search-input')?.value.trim(),
            price_min: parseInputNumber('price_min'),
            price_max: parseInputNumber('price_max'),
            sale: document.getElementById('sale_checkbox')?.checked
        };

        const labels = [];
        if (appliedFilters.category) labels.push(`Категория: ${appliedFilters.category}`);
        if (appliedFilters.title) labels.push(`Поиск: ${appliedFilters.title}`);
        if (appliedFilters.price_min !== undefined) labels.push(`Цена от: ${appliedFilters.price_min}`);
        if (appliedFilters.price_max !== undefined) labels.push(`Цена до: ${appliedFilters.price_max}`);
        if (appliedFilters.sale) labels.push('Только акции');

        activeFilters.textContent = labels.join(', ');
    }

    function parseInputNumber(id) {
        const value = parseFloat(document.getElementById(id)?.value);
        return isNaN(value) ? undefined : value;
    }

    // --- Поиск ---
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

    document.getElementById('sale_checkbox')?.addEventListener('change', () => {
        updateActiveFilters();
    });

    function truncateText(text, maxChars = 100) {
        if (!text) return '';
        if (text.length <= maxChars) return text;
        const truncated = text.substring(0, maxChars);
        const lastSpace = truncated.lastIndexOf(' ');
        const cutIndex = lastSpace > maxChars * 0.7 ? lastSpace : maxChars; // не резать слишком рано
        return truncated.substring(0, cutIndex).trim() + '…';
    }

    // --- Загрузка товаров ---
    async function loadProducts(page = 1) {
        try {
            const params = new URLSearchParams();
            if (appliedFilters.category) params.append('category', appliedFilters.category);
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

                // Заполняем данные
                img.src = `/static${product.img_url}`;
                img.alt = product.title;
                articleNum.textContent = `Артикул: ${product.article_num}`;
                titleLink.textContent = product.title;
                titleLink.href = `/product/${product.id}`;
                price.textContent = `${product.price} ₽`;
                description.textContent = truncateText(product.description, 100);

                if (product.sale) {
                    badge.style.display = 'flex';
                } else {
                    badge.style.display = 'none';
                }

                // === ДОБАВЛЯЕМ КНОПКИ КОРЗИНЫ ===
                const blockBuy = clone.querySelector('.block_buy');
                if (blockBuy) {
                    // Создаём блок .user-actions
                    const userActions = document.createElement('div');
                    userActions.className = 'user-actions';
                    
                    // Кнопка "Купить"
                    const buyBtn = document.createElement('div');
                    buyBtn.className = 'btn_buy';
                    buyBtn.dataset.productId = product.id;
                    buyBtn.innerHTML = '<div class="btn_text"></div>Купить';

                    // Иконка корзины
                    const cartLink = document.createElement('a');
                    cartLink.href = '#';
                    cartLink.className = 'cart-icon';
                    cartLink.title = 'Добавить в корзину';
                    cartLink.dataset.productId = product.id;
                    cartLink.innerHTML = `<img class="img_c" src="/static/img/other/cart-add-mini.svg" alt="В корзину" width="25" height="25">`;

                    // Собираем блок
                    userActions.appendChild(buyBtn);
                    userActions.appendChild(cartLink);
                    blockBuy.appendChild(userActions);

                    // Управление видимостью
                    if (window.userRole === 'user') {
                        userActions.style.display = ''; // показываем
                    } else {
                        userActions.style.display = 'none'; // скрываем
                    }
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