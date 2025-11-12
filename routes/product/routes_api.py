import logging
import os
from flask import Blueprint, request, jsonify, current_app
from models import User, Shop, db
from utils.add_img import save_product_image
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from pathlib import Path


api_bp = Blueprint('api', __name__, url_prefix='/api')



@api_bp.route('/products/<int:id>', methods=['GET'])
def get_product_by_id(id):
    """
    Получить данные одного товара по ID.
    Доступен всем, включая гостей.
    """
    product = Shop.query.get(id)
    if not product:
        return jsonify({"error": "Товар не найден"}), 404

    return jsonify({
        "id": product.id,
        "article_num": product.article_num,
        "user_id": product.user_id,
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "quantity": product.quantity,
        "img_url": product.link_img,
        "created_at": product.created_at.isoformat(),
        "sale": product.sale,
        "category": product.category
    }), 200

@api_bp.route('/products', methods=['GET'])
def get_all_products():
    """Получить список товаров с фильтрами, сортировкой и пагинацией"""
    
    args = request.args
    query = Shop.query

    # === Фильтр по владельцу (user_id) ===
    user_id_param = args.get('user_id', type=int)
    if user_id_param is not None:
        # Фильтруем только товары указанного пользователя
        query = query.filter(Shop.user_id == user_id_param)

    # === Фильтр по категории ===
    categories = args.getlist('category')
    if categories:
        # Очистка: удаляем пустые и лишние пробелы
        clean_categories = [c.strip() for c in categories if c.strip()]
        if clean_categories:
            query = query.filter(Shop.category.in_(clean_categories))

    # === Фильтр по названию ===
    title = args.get('title')
    if title:
        query = query.filter(Shop.title.ilike(f"%{title}%"))

    # === Фильтр по цене ===
    price_min = args.get('price_min', type=float)
    price_max = args.get('price_max', type=float)
    if price_min is not None and price_max is not None:
        if price_min > price_max:
            return jsonify({"error": "price_min не может быть больше price_max"}), 400
        query = query.filter(Shop.price.between(price_min, price_max))
    elif price_min is not None:
        if price_min < 0:
            return jsonify({"error": "price_min не может быть отрицательным"}), 400
        query = query.filter(Shop.price >= price_min)
    elif price_max is not None:
        if price_max < 0:
            return jsonify({"error": "price_max не может быть отрицательным"}), 400
        query = query.filter(Shop.price <= price_max)

    # === Фильтр по количеству ===
    quantity = args.get('quantity', type=int)
    quantity_min = args.get('quantity_min', type=int)
    quantity_max = args.get('quantity_max', type=int)
    
    if quantity is not None:
        if quantity < 0:
            return jsonify({"error": "Количество не может быть отрицательным"}), 400
        query = query.filter(Shop.quantity == quantity)
    else:
        if quantity_min is not None:
            if quantity_min < 0:
                return jsonify({"error": "quantity_min не может быть отрицательным"}), 400
            query = query.filter(Shop.quantity >= quantity_min)
        if quantity_max is not None:
            if quantity_max < 0:
                return jsonify({"error": "quantity_max не может быть отрицательным"}), 400
            query = query.filter(Shop.quantity <= quantity_max)

    # === Фильтр по дате создания ===
    date_exact = args.get('date')
    date_from = args.get('date_from')
    date_to = args.get('date_to')

    if date_exact:
        try:
            dt = datetime.strptime(date_exact, "%d.%m.%Y")
            query = query.filter(db.func.date(Shop.created_at) == dt.date())
        except ValueError:
            return jsonify({"error": "Неверный формат даты. Используйте дд.мм.гггг"}), 400
    else:
        if date_from:
            try:
                dt_from = datetime.strptime(date_from, "%d.%m.%Y")
                query = query.filter(Shop.created_at >= dt_from)
            except ValueError:
                return jsonify({"error": "Неверный формат date_from. Используйте дд.мм.гггг"}), 400
        if date_to:
            try:
                dt_to = datetime.strptime(date_to, "%d.%m.%Y") + timedelta(days=1)
                query = query.filter(Shop.created_at < dt_to)
            except ValueError:
                return jsonify({"error": "Неверный формат date_to. Используйте дд.мм.гггг"}), 400

    # === Фильтр по акции ===
    sale = args.get('sale')
    if sale is not None:
        sale_lower = sale.lower()
        if sale_lower in ('true', '1', 'on', 'yes'):
            query = query.filter(Shop.sale == True)
        elif sale_lower in ('false', '0', 'off', 'no'):
            query = query.filter(Shop.sale == False)
        else:
            return jsonify({"error": "Параметр sale должен быть булевым (true/false, 1/0)"}), 400

    # === Сортировка ===
    sort_param = args.get('sort')
    sort_mapping = {
        'title_asc': Shop.title.asc(),
        'title_desc': Shop.title.desc(),
        'article_num_asc': Shop.article_num.asc(),
        'article_num_desc': Shop.article_num.desc(),
        'price_asc': Shop.price.asc(),
        'price_desc': Shop.price.desc(),
        'quantity_asc': Shop.quantity.asc(),
        'quantity_desc': Shop.quantity.desc(),
        'created_at_asc': Shop.created_at.asc(),
        'created_at_desc': Shop.created_at.desc(),
    }

    if sort_param:
        if sort_param not in sort_mapping:
            return jsonify({"error": f"Недопустимое значение сортировки: {sort_param}"}), 400
        query = query.order_by(sort_mapping[sort_param])
    else:
        # Сортировка по умолчанию: новые товары сверху
        query = query.order_by(Shop.created_at.desc())

    # === Пагинация или все товары ===
    if args.get('all') is not None:
        products = query.all()
        result = {
            "items": [{
                "id": p.id,
                "article_num": p.article_num,
                "user_id": p.user_id,
                "title": p.title,
                "description": p.description,
                "price": p.price,
                "quantity": p.quantity,
                "img_url": p.link_img,
                "created_at": p.created_at.isoformat(),
                "sale": p.sale,
                "category": p.category
            } for p in products],
            "total": len(products),
            "all": True
        }
        return jsonify(result)

    # Пагинация по умолчанию
    page = args.get('page', 1, type=int)
    per_page = args.get('per_page', 8, type=int)

    if per_page > 100:
        per_page = 100
    if page < 1:
        page = 1

    try:
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    except Exception as e:
        logging.error(f"Ошибка пагинации: {e}")
        return jsonify({"error": "Ошибка при получении товаров"}), 500

    result = {
        "items": [{
            "id": p.id,
            "article_num": p.article_num,
            "user_id": p.user_id,
            "title": p.title,
            "description": p.description,
            "price": p.price,
            "quantity": p.quantity,
            "img_url": p.link_img,
            "created_at": p.created_at.isoformat(),
            "sale": p.sale,
            "category": p.category
        } for p in paginated.items],
        "total_pages": paginated.pages,
        "current_page": paginated.page,
        "per_page": paginated.per_page,
        "total_items": paginated.total
    }

    return jsonify(result)


@api_bp.route('/products', methods=['POST'])
@jwt_required()
def add_product():
    """
    Добавить новый товар.
    Ожидает multipart/form-data с полями:
    name, description, price, quantity, article-number, category, sale (опционально), image
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    # Получение данных из формы
    title = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price_str = request.form.get('price', '').strip()
    quantity_str = request.form.get('quantity', '').strip()
    article_num = request.form.get('article-number', '').strip()
    category = request.form.get('category', '').strip()
    sale = request.form.get('sale', '')
    image_file = request.files.get('image')

    # Проверка обязательных полей
    required_fields = {
        'Название товара': title,
        'Описание товара': description,
        'Цена': price_str,
        'Количество': quantity_str,
        'Артикул': article_num,
        'Категория': category
    }

    missing = [field for field, value in required_fields.items() if not value]
    if missing:
        return jsonify({"error": f"Не заполнены обязательные поля: {', '.join(missing)}"}), 400

    # Валидация и преобразование цены
    try:
        price = float(price_str)
        if price < 0:
            return jsonify({"error": "Цена не может быть отрицательной"}), 400
    except ValueError:
        return jsonify({"error": "Цена должна быть числом"}), 400

    # Валидация и преобразование количества
    try:
        quantity = int(quantity_str)
        if quantity < 0:
            return jsonify({"error": "Количество не может быть отрицательным"}), 400
    except ValueError:
        return jsonify({"error": "Количество должно быть целым числом"}), 400

    # Проверка изображения
    if not image_file or not image_file.filename:
        return jsonify({"error": "Изображение не выбрано"}), 400

    try:
        link_img = save_product_image(image_file)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Ошибка сохранения изображения: {e}")
        return jsonify({"error": "Ошибка при загрузке изображения"}), 500

    # Обработка флага sale
    sale_lower = sale.lower() if sale else ''
    is_sale = sale_lower in ('true', '1', 'on', 'yes')

    # Проверка уникальности артикула (если требуется)
    if Shop.query.filter_by(article_num=article_num).first():
        return jsonify({"error": "Товар с таким артикулом уже существует"}), 409

    # Создание и сохранение товара
    try:
        new_product = Shop(
            user_id=user.id,
            article_num=article_num,
            title=title,
            description=description,
            price=price,
            quantity=quantity,
            link_img=link_img,
            category=category,
            sale=is_sale
        )
        db.session.add(new_product)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Товар успешно добавлен",
            "product_id": new_product.id,
            "link_img": new_product.link_img
        }), 201

    except Exception as e:
        db.session.rollback()
        logging.exception("Ошибка при добавлении товара в БД")
        return jsonify({"error": "Ошибка при добавлении товара в базу данных"}), 500


@api_bp.route('/products/<int:id>', methods=['PUT'])
@jwt_required()
def update_product(id):
    """
    Обновить существующий товар.
    Поддерживает:
      - application/json (тело с полями)
      - multipart/form-data (форма с изображением)
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    # Получаем товар ТОЛЬКО по ID (без привязки к user_id)
    product = Shop.query.get(id)
    if not product:
        return jsonify({"error": "Товар не найден"}), 404

    # Проверка прав доступа: админ — может всё, остальные — только свои
    if user.role != 'admin' and int(product.user_id) != int(current_user_id):
        return jsonify({"error": "Товар не найден или недоступен"}), 404

    # Определяем тип запроса
    is_json = request.is_json

    if is_json:
        data = request.get_json() or {}
        image_file = None
    else:
        data = {}  # не используется при form-data
        image_file = request.files.get('image')

    try:
        # Название
        title = data.get('title') if is_json else request.form.get('title')
        if title is not None:
            title = title.strip()
            if not title:
                return jsonify({"error": "Название товара не может быть пустым"}), 400
            product.title = title

        # Описание
        description = data.get('description') if is_json else request.form.get('description')
        if description is not None:
            product.description = str(description).strip()

        # Категория
        category = data.get('category') if is_json else request.form.get('category')
        if category is not None:
            category = str(category).strip()
            if not category:
                return jsonify({"error": "Категория не может быть пустой"}), 400
            product.category = category

        # Артикул
        article_num_input = data.get('article_num') if is_json else request.form.get('article_num')
        if article_num_input is not None:
            article_num_input = str(article_num_input).strip()
            if not article_num_input:
                return jsonify({"error": "Артикул не может быть пустым"}), 400
            # Проверяем уникальность артикула (кроме текущего товара)
            existing = Shop.query.filter(
                Shop.article_num == article_num_input,
                Shop.id != id
            ).first()
            if existing:
                return jsonify({"error": "Товар с таким артикулом уже существует"}), 409
            product.article_num = article_num_input

        # Цена
        price_input = data.get('price') if is_json else request.form.get('price')
        if price_input is not None:
            try:
                price = float(price_input)
                if price < 0:
                    return jsonify({"error": "Цена не может быть отрицательной"}), 400
                product.price = price
            except (ValueError, TypeError):
                return jsonify({"error": "Цена должна быть числом"}), 400

        # Количество
        quantity_input = data.get('quantity') if is_json else request.form.get('quantity')
        if quantity_input is not None:
            try:
                quantity = int(quantity_input)
                if quantity < 0:
                    return jsonify({"error": "Количество не может быть отрицательным"}), 400
                product.quantity = quantity
            except (ValueError, TypeError):
                return jsonify({"error": "Количество должно быть целым числом"}), 400

        # Акция (sale)
        if is_json:
            sale_input = data.get('sale')
            if sale_input is not None:
                if isinstance(sale_input, bool):
                    product.sale = sale_input
                else:
                    return jsonify({"error": "Поле 'sale' должно быть булевым"}), 400
        else:
            # В form-data чекбокс присутствует только если отмечен
            product.sale = 'sale' in request.form

        # Изображение
        if image_file and image_file.filename:
            try:
                product.link_img = save_product_image(image_file)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logging.error(f"Ошибка загрузки изображения при обновлении: {e}")
                return jsonify({"error": "Ошибка при загрузке изображения"}), 500

        # Сохраняем изменения
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Товар успешно обновлён",
            "product": {
                "id": product.id,
                "article_num": product.article_num,
                "user_id": product.user_id,
                "title": product.title,
                "description": product.description,
                "price": product.price,
                "quantity": product.quantity,
                "img_url": product.link_img,
                "created_at": product.created_at.isoformat(),
                "sale": product.sale,
                "category": product.category
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        logging.exception("Неожиданная ошибка при обновлении товара")
        return jsonify({"error": "Ошибка при обновлении товара"}), 500


@api_bp.route('/products/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_product(id):
    """
    Удалить товар по ID.
    - Админ может удалить любой товар.
    - Продавец — только свои.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    # Получаем товар по ID
    product = Shop.query.get(id)
    if not product:
        return jsonify({"error": "Товар не найден"}), 404

    # Проверка прав:
    # - Админ может удалить всё
    # - Продавец — только своё
    if user.role == 'suser' and int(product.user_id) != int(current_user_id):
        return jsonify({"error": "Нет прав доступа. Вы можете удалять только свои товары."}), 403

    try:
        if product.link_img and product.link_img != "/img/avatars/default_product.png":
            try:
                relative_path = product.link_img.lstrip("/")
                full_path = Path(current_app.static_folder) / relative_path
                if full_path.exists():
                    os.remove(full_path)
            except Exception as e:
                logging.warning(f"Не удалось удалить файл изображения {full_path}: {e}")

        db.session.delete(product)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Товар успешно удалён"
        }), 200

    except Exception as e:
        db.session.rollback()
        logging.exception("Ошибка при удалении товара")
        return jsonify({"error": "Ошибка при удалении товара"}), 500
    