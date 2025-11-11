document.addEventListener('DOMContentLoaded', function () {
    // === Элементы DOM ===
    const filterForm = document.getElementById('filter-form');
    const sortSelect = document.getElementById('sort-select');
    const categorySelect = document.getElementById('category-select');
    const searchInput = document.getElementById('search-input');
    const saleOnlyCheckbox = document.getElementById('sale-only-checkbox');
    const infoPanel = document.getElementById('info-panel');
    const gridBody = document.getElementById('products-grid-body');

    let isLoading = false;
    let isInitialized = false;
    let currentProductCount = 0; // Хранение количества

    // === Вспомогательные функции ===

    function showMessage(text, type = 'info') {
        infoPanel.textContent = text;
        infoPanel.className = 'info-messages ' + type;
        infoPanel.classList.remove('hidden');
    }

    function getFilters() {
        return {
            sort: sortSelect?.value || '',
            category: categorySelect?.value || '',
            search: searchInput?.value.trim() || '',
            sale_only: saleOnlyCheckbox?.checked || false
        };
    }

    function clearGrid() {
        if (gridBody) gridBody.innerHTML = '';
    }

    // === Загрузка товаров ===
    async function loadProducts() {
        if (isLoading) return;
        isLoading = true;

        clearGrid();
        showMessage('Загрузка...', 'info');

        const filters = getFilters();
        const url = new URL('/api/products', window.location.origin);
        url.searchParams.append('all', '1');

        // Фильтрация по роли пользователя
        if (window.CURRENT_USER_ROLE === 'suser' && window.CURRENT_USER_ID) {
            url.searchParams.append('user_id', window.CURRENT_USER_ID);
        }

        // Применение фильтров
        if (filters.sort) url.searchParams.append('sort', filters.sort);
        if (filters.category) url.searchParams.append('category', filters.category);
        if (filters.search) url.searchParams.append('title', filters.search);
        if (filters.sale_only) url.searchParams.append('sale', 'true');

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();

            if (data.items && Array.isArray(data.items) && data.items.length > 0) {
                const template = document.getElementById('product-row-template');
                if (!template) {
                    throw new Error('Шаблон product-row-template не найден');
                }

                data.items.forEach(product => {
                    const fragment = template.content.cloneNode(true);
                    const row = fragment.querySelector('.product-row');
                    if (!row) return;

                    // ID
                    const idCell = row.querySelector('.id-cell');
                    if (idCell) idCell.textContent = product.id;

                    // Артикул
                    const articleCell = row.querySelector('.article-cell');
                    if (articleCell) articleCell.textContent = product.article_num || '—';

                    // ID manager (suser)
                    const sellerIdCell = row.querySelector('.seller-id-cell');
                    if (sellerIdCell) sellerIdCell.textContent = product.user_id || '—';

                    // Изображение
                    const img = row.querySelector('.thumbnail');
                    if (img) {
                        if (product.img_url) {
                            img.src = `/static${product.img_url}`;
                            img.alt = product.title || 'Товар';
                            img.style.display = 'block';
                        } else {
                            img.style.display = 'none';
                        }
                    }

                    // Название + всплывающее описание
                    const nameLink = row.querySelector('.name-cell a');
                    if (nameLink) {
                        nameLink.textContent = product.title || '—';
                        nameLink.href = `/product/${product.id}`;
                        // Устанавливаем описание как подсказку при наведении
                        nameLink.title = product.description 
                            ? `Описание: ${product.description}` 
                            : 'Описание отсутствует';
                    }

                    // Описание
                    const descCell = row.querySelector('.description-cell');
                    if (descCell) descCell.textContent = product.description || '—';

                    // Цена
                    const priceCell = row.querySelector('.price-cell');
                    if (priceCell) {
                        priceCell.textContent = product.price ? `${product.price} ₽` : '—';
                    }

                    // Количество
                    const qtyCell = row.querySelector('.quantity-cell');
                    if (qtyCell) {
                        qtyCell.textContent = product.quantity !== undefined && product.quantity !== null
                            ? product.quantity
                            : '—';
                    }

                    // Категория
                    const catCell = row.querySelector('.category-cell');
                    if (catCell) catCell.textContent = product.category || '—';

                    // Дата создания
                    const dateCell = row.querySelector('.created-at-cell');
                    if (dateCell && product.created_at) {
                        const date = new Date(product.created_at);
                        if (!isNaN(date.getTime())) {
                            dateCell.textContent = date.toLocaleString('ru-RU', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                            });
                        } else {
                            dateCell.textContent = '—';
                        }
                    } else if (dateCell) {
                        dateCell.textContent = '—';
                    }

                    // Распродажа
                    const badge = row.querySelector('.badge_edit');
                    if (badge) {
                        
                        if (product.sale) {
                            badge.textContent = 'Акция';
                            badge.style.display = 'inline-block';
                        } else {
                            badge.style.display = 'none';
                            // textContent можно не очищать, но лучше для чистоты:
                            badge.textContent = '';
                        }
                    }

                    // Кнопки действий
                    const editBtn = row.querySelector('.edit-icon');
                    if (editBtn) {
                        editBtn.href = `/edit-product/${product.id}`;
                    }

                    const removeBtn = row.querySelector('.remove-icon');
                    if (removeBtn) {
                        removeBtn.addEventListener('click', async function (e) {
                            e.preventDefault();

                            if (!confirm('Вы уверены, что хотите удалить товар?')) return;

                            try {
                                const response = await fetch(`/api/products/${product.id}`, {
                                    method: 'DELETE',
                                    credentials: 'same-origin'
                                });

                                const result = await response.json();

                                if (response.ok) {
                                    // Удаляем строку из DOM
                                    const rowToRemove = row.closest('.product-row');
                                    if (rowToRemove) rowToRemove.remove();

                                    // Обновляем счётчик
                                    currentProductCount = Math.max(0, currentProductCount - 1);

                                    if (currentProductCount > 0) {
                                        showMessage(`Загружено товаров: ${currentProductCount}`, 'info');
                                    } else {
                                        showMessage('Товары не найдены', 'warning');
                                        clearGrid(); // на случай, если остались "мёртвые" элементы
                                    }
                                } else {
                                    const errorMsg = result.error || `Ошибка ${response.status}`;
                                    alert('Ошибка: ' + errorMsg);
                                }
                            } catch (error) {
                                console.error('Ошибка сети при удалении:', error);
                                alert('Не удалось подключиться к серверу');
                            }
                        });
                    }

                    gridBody.appendChild(fragment);
                });

                currentProductCount = data.items.length;
                showMessage(`Загружено товаров: ${currentProductCount}`, 'info');
            } else {
                currentProductCount = 0;
                showMessage('Товары не найдены', 'warning');
            }
        } catch (error) {
            console.error('Ошибка загрузки товаров:', error);
            showMessage('Не удалось загрузить товары. Попробуйте позже.', 'error');
            currentProductCount = 0;
        } finally {
            isLoading = false;
        }
    }

    // === Обработчики событий ===
    if (filterForm) {
        filterForm.addEventListener('submit', function (e) {
            e.preventDefault();
            loadProducts();
        });
    }

    // === Инициализация ===
    function init() {
        if (isInitialized) return;
        isInitialized = true;
        loadProducts();
    }

    init();
});