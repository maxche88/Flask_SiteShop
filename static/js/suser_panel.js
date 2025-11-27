// Панель управления товарами — менеджер (suser)

document.addEventListener('DOMContentLoaded', function () {
    const selectAllCheckbox = document.getElementById('select-all');
    const gridBody = document.getElementById('products-grid-body');
    const infoPanel = document.getElementById('info-panel');

    const searchInput = document.getElementById('search-input');
    const sortSelect = document.getElementById('sort-select');
    const priceMinInput = document.getElementById('price_min');
    const priceMaxInput = document.getElementById('price_max');
    const saleCheckbox = document.getElementById('sale-checkbox');
    const categoryCheckboxes = document.querySelectorAll('input[name="category"]');
    const toggleFiltersBtn = document.getElementById('toggle-filters');
    const advancedFilters = document.getElementById('advanced-filters');
    const clearFiltersBtn = document.getElementById('clear-filters');
    const searchBtn = document.getElementById('search-btn');

    // Элементы для массового назначения UID
    const btnUpdateUid = document.getElementById('btnUpdateUid');
    const uidInput = document.getElementById('uid-input');

    let isLoading = false;
    let currentProductCount = 0;

    // === Вспомогательные функции ===

    function showMessage(text, type = 'info') {
        infoPanel.textContent = text;
        infoPanel.className = 'info-messages ' + type;
        infoPanel.classList.remove('hidden');
    }

    function clearGrid() {
        if (gridBody) gridBody.innerHTML = '';
    }

    function parseInputNumber(id) {
        const el = document.getElementById(id);
        if (!el) return undefined;
        const value = parseFloat(el.value);
        return isNaN(value) ? undefined : value;
    }

    // Обновление состояния кнопки "Назначить uid"
    function updateAssignButtonState() {
        const anyChecked = gridBody.querySelectorAll('.row-checkbox:checked').length > 0;
        if (btnUpdateUid) btnUpdateUid.disabled = !anyChecked;
        if (uidInput) uidInput.disabled = !anyChecked;
    }

    // === Обработчики чекбоксов ===

    if (selectAllCheckbox && gridBody) {
        selectAllCheckbox.addEventListener('change', function () {
            const checkboxes = gridBody.querySelectorAll('.row-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = selectAllCheckbox.checked;
            });
            updateAssignButtonState();
        });

        gridBody.addEventListener('change', function (e) {
            if (e.target.classList.contains('row-checkbox')) {
                const allCheckboxes = gridBody.querySelectorAll('.row-checkbox');
                const allChecked = Array.from(allCheckboxes).every(cb => cb.checked);
                selectAllCheckbox.checked = allChecked;
                updateAssignButtonState();
            }
        });
    }

    // === Отправка массового назначения UID ===

    if (btnUpdateUid) {
        btnUpdateUid.addEventListener('click', async function () {
            const uidValue = uidInput?.value?.trim();
            if (!uidValue) {
                alert('Пожалуйста, введите ID пользователя');
                return;
            }

            const uid = parseInt(uidValue, 10);
            if (uid <= 0 || !Number.isInteger(uid)) {
                alert('ID должен быть положительным целым числом');
                return;
            }

            const checkedCheckboxes = gridBody.querySelectorAll('.row-checkbox:checked');
            const productIds = Array.from(checkedCheckboxes)
                .map(cb => cb.closest('.product-row')?.dataset.productId)
                .filter(id => id); // игнорируем строки без data-product-id

            if (productIds.length === 0) {
                alert('Не выбрано ни одного товара');
                return;
            }

            try {
                const response = await fetch('/api/products/assign-uid', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        product_ids: productIds,
                        new_user_id: uid
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    alert('UID успешно назначен');
                    loadProducts(); // перезагрузить список
                } else {
                    alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
                }
            } catch (error) {
                console.error('Ошибка при назначении UID:', error);
                alert('Ошибка сети. Проверьте консоль.');
            }
        });
    }

    // === Получение текущих фильтров ===
    function getFilters() {
        const selectedCategories = Array.from(categoryCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        return {
            title: searchInput?.value.trim() || '',
            sort: sortSelect?.value || '',
            price_min: parseInputNumber('price_min'),
            price_max: parseInputNumber('price_max'),
            sale: saleCheckbox?.checked || false,
            categories: selectedCategories.length ? selectedCategories : null
        };
    }

    // === Загрузка товаров ===
    async function loadProducts() {
        if (isLoading) return;
        isLoading = true;

        clearGrid();
        if (selectAllCheckbox) selectAllCheckbox.checked = false;
        updateAssignButtonState();
        showMessage('Загрузка...', 'info');

        const filters = getFilters();
        const url = new URL('/api/products', window.location.origin);
        url.searchParams.append('all', '1');

        // Фильтр по владельцу (только свои товары для suser)
        if (window.CURRENT_USER_ROLE === 'suser' && window.CURRENT_USER_ID) {
            url.searchParams.append('user_id', window.CURRENT_USER_ID);
        }

        // Применение фильтров
        if (filters.title) url.searchParams.append('title', filters.title);
        if (filters.sort) url.searchParams.append('sort', filters.sort);
        if (filters.price_min !== undefined) url.searchParams.append('price_min', filters.price_min);
        if (filters.price_max !== undefined) url.searchParams.append('price_max', filters.price_max);
        if (filters.sale) url.searchParams.append('sale', 'true');
        if (filters.categories) {
            filters.categories.forEach(cat => {
                url.searchParams.append('category', cat);
            });
        }

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: { 'Accept': 'application/json' },
                credentials: 'same-origin'
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();

            if (data.items?.length) {
                const template = document.getElementById('product-row-template');
                if (!template) throw new Error('Шаблон не найден');

                data.items.forEach(product => {
                    const fragment = template.content.cloneNode(true);
                    const row = fragment.querySelector('.product-row');
                    if (!row) return;

                    // Присваиваем data-product-id для массовых операций
                    row.dataset.productId = product.id;

                    // ID
                    const idCell = row.querySelector('.id-cell');
                    if (idCell) idCell.textContent = product.id;

                    // Артикул
                    const articleCell = row.querySelector('.article-cell');
                    if (articleCell) articleCell.textContent = product.article_num || '—';

                    // ID продавца
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

                    const imageLink = row.querySelector('.product-image-link');
                    if (imageLink) {
                        imageLink.href = `/product/${product.id}`;
                        imageLink.title = product.title || 'Открыть карточку товара';
                    }

                    // Название
                    const nameLink = row.querySelector('.name-cell a');
                    if (nameLink) {
                        nameLink.textContent = product.title || '—';
                        nameLink.href = `/product/${product.id}`;
                        nameLink.title = product.description 
                            ? `Описание: ${product.description}` 
                            : 'Описание отсутствует';
                    }

                    
                    // Цена
                    const priceCell = row.querySelector('.price-cell');
                    if (priceCell) {
                        priceCell.textContent = product.price ? `${product.price} ₽` : '—';
                    }

                    // Количество
                    const qtyCell = row.querySelector('.quantity-cell');
                    if (qtyCell) {
                        qtyCell.textContent = product.quantity ?? '—';
                    }

                    // Категория
                    const catCell = row.querySelector('.category-cell');
                    if (catCell) catCell.textContent = product.category || '—';

                    // Дата
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

                    // Акция
                    const badge = row.querySelector('.badge_edit');
                    if (badge) {
                        if (product.sale) {
                            badge.textContent = 'Акция';
                            badge.style.display = 'inline-block';
                        } else {
                            badge.style.display = 'none';
                            badge.textContent = '';
                        }
                    }

                    // Кнопки редактирования и удаления
                    const editBtn = row.querySelector('.edit-icon');
                    if (editBtn) {
                        // При клике кнопка ведёт на страницу редактирования
                        const link = document.createElement('a');
                        link.href = `/edit-product/${product.id}`;
                        link.style.display = 'contents';
                        editBtn.replaceWith(link);
                        link.appendChild(editBtn.cloneNode(true));
                    }

                    const removeBtn = row.querySelector('.remove-icon');
                    if (removeBtn) {
                        removeBtn.addEventListener('click', async function (e) {
                            e.preventDefault();
                            if (!confirm('Удалить товар?')) return;

                            try {
                                const res = await fetch(`/api/products/${product.id}`, {
                                    method: 'DELETE',
                                    credentials: 'same-origin'
                                });
                                const result = await res.json();

                                if (res.ok) {
                                    row.remove();
                                    currentProductCount = Math.max(0, currentProductCount - 1);
                                    showMessage(
                                        currentProductCount > 0 
                                            ? `Загружено товаров: ${currentProductCount}` 
                                            : 'Товары не найдены',
                                        currentProductCount > 0 ? 'info' : 'warning'
                                    );
                                } else {
                                    alert('Ошибка: ' + (result.error || res.status));
                                }
                            } catch (err) {
                                console.error('Ошибка удаления:', err);
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
            console.error('Ошибка загрузки:', error);
            showMessage('Не удалось загрузить товары', 'error');
        } finally {
            isLoading = false;
        }
    }

    // === Обработчики фильтров ===

    toggleFiltersBtn?.addEventListener('click', () => {
        advancedFilters.classList.toggle('advanced_filters--visible');
    });

    function applyFilters() {
        loadProducts();
    }

    searchBtn?.addEventListener('click', applyFilters);
    searchInput?.addEventListener('keypress', e => {
        if (e.key === 'Enter') applyFilters();
    });

    sortSelect?.addEventListener('change', applyFilters);
    saleCheckbox?.addEventListener('change', applyFilters);
    priceMinInput?.addEventListener('change', applyFilters);
    priceMaxInput?.addEventListener('change', applyFilters);
    categoryCheckboxes.forEach(cb => {
        cb.addEventListener('change', applyFilters);
    });

    clearFiltersBtn?.addEventListener('click', () => {
        searchInput.value = '';
        sortSelect.value = '';
        priceMinInput.value = '';
        priceMaxInput.value = '';
        saleCheckbox.checked = false;
        categoryCheckboxes.forEach(cb => cb.checked = false);
        applyFilters();
    });

    // Инициализация
    loadProducts();
});