import logging
import os
from flask import Blueprint, request, jsonify, current_app, g
from models import User, Shop
from extensions import db
from utils.add_img import save_product_image
from datetime import datetime, timedelta
from pathlib import Path


api_bp = Blueprint('api', __name__, url_prefix='/api')
product_logger = logging.getLogger('app.product')


@api_bp.route('/products/<int:id>', methods=['GET'])
def get_product_by_id(id):
    """
    Получить данные одного товара по ID.
    Доступен всем, включая гостей.
    """
    product = db.session.get(Shop, id)
    if not product:
        product_logger.info(f"Запрос несуществующего товара с ID={id}")
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
        query = query.filter(Shop.user_id == user_id_param)

    # === Фильтр по категории ===
    categories = args.getlist('category')
    if categories:
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
        query = query.order_by(Shop.created_at.desc())

    # === Пагинация или все товары ===
    if args.get('all') is not None:
        try:
            products = query.all()
        except Exception as e:
            product_logger.error(f"Ошибка при получении всех товаров: {e}")
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
            } for p in products],
            "total": len(products),
            "all": True
        }
        product_logger.info("Запрошены все товары (без пагинации)")
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
        product_logger.error(f"Ошибка пагинации при запросе товаров: {e}")
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

    product_logger.info(f"Запрос списка товаров: page={page}, per_page={per_page}, filters={dict(args)}")
    return jsonify(result)


@api_bp.route('/products/assign-uid', methods=['POST'])
def assign_user_to_products():
    """
    Назначить user_id выбранным товарам.
    Доступно только suser и admin.
    """
    # Используем пользователя из g (уже проверен в before_request)
    current_user = g.current_user

    if current_user.role not in ('suser', 'admin'):
        return jsonify({"error": "Недостаточно прав"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Тело запроса пустое"}), 400

    product_ids = data.get('product_ids')
    new_user_id = data.get('new_user_id')

    if not product_ids or not isinstance(product_ids, list) or len(product_ids) == 0:
        return jsonify({"error": "Необходимо указать хотя бы один ID товара"}), 400

    if not new_user_id or not isinstance(new_user_id, int) or new_user_id <= 0:
        return jsonify({"error": "new_user_id должен быть положительным целым числом"}), 400

    # Проверяем, существует ли целевой пользователь и его роль
    target_user = db.session.get(User, new_user_id)
    if not target_user:
        return jsonify({"error": "Пользователь с таким ID не найден"}), 404

    if target_user.role not in ('suser', 'admin'):
        return jsonify({"error": "Нельзя назначить товар пользователю без роли suser или admin"}), 400

    try:
        products = Shop.query.filter(Shop.id.in_(product_ids)).all()
        if len(products) != len(product_ids):
            found_ids = {p.id for p in products}
            missing = [pid for pid in product_ids if pid not in found_ids]
            return jsonify({"error": f"Товары не найдены: {missing}"}), 404

        for product in products:
            product.user_id = new_user_id

        db.session.commit()
        product_logger.info(f"Пользователь {g.current_user_id} назначил user_id={new_user_id} для товаров: {product_ids}")
        return jsonify({
            "success": True,
            "message": f"UID {new_user_id} успешно назначен {len(products)} товарам"
        }), 200

    except Exception as e:
        db.session.rollback()
        product_logger.exception(f"Ошибка при назначении UID {new_user_id} товарам {product_ids}: {e}")
        return jsonify({"error": "Ошибка при обновлении базы данных"}), 500


@api_bp.route('/products', methods=['POST'])
def add_product():
    """
    Добавить новый товар.
    Ожидает multipart/form-data с полями:
    name, description, price, quantity, article-number, category, sale (опционально), image
    """
    user = g.current_user

    title = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price_str = request.form.get('price', '').strip()
    quantity_str = request.form.get('quantity', '').strip()
    article_num = request.form.get('article-number', '').strip()
    category = request.form.get('category', '').strip()
    sale = request.form.get('sale', '')
    image_file = request.files.get('image')

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
        product_logger.info(f"Пропущены обязательные поля при добавлении товара от user_id={user.id}: {missing}")
        return jsonify({"error": f"Не заполнены обязательные поля: {', '.join(missing)}"}), 400

    try:
        price = float(price_str)
        if price < 0:
            return jsonify({"error": "Цена не может быть отрицательной"}), 400
    except ValueError:
        return jsonify({"error": "Цена должна быть числом"}), 400

    try:
        quantity = int(quantity_str)
        if quantity < 0:
            return jsonify({"error": "Количество не может быть отрицательным"}), 400
    except ValueError:
        return jsonify({"error": "Количество должно быть целым числом"}), 400

    if not image_file or not image_file.filename:
        return jsonify({"error": "Изображение не выбрано"}), 400

    try:
        link_img = save_product_image(image_file)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        product_logger.error(f"Ошибка сохранения изображения для user_id={user.id}: {e}")
        return jsonify({"error": "Ошибка при загрузке изображения"}), 500

    sale_lower = sale.lower() if sale else ''
    is_sale = sale_lower in ('true', '1', 'on', 'yes')

    if Shop.query.filter_by(article_num=article_num).first():
        product_logger.warning(f"Попытка добавить товар с уже существующим артикулом '{article_num}' от user_id={user.id}")
        return jsonify({"error": "Товар с таким артикулом уже существует"}), 409

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

        product_logger.info(f"Товар успешно создан: product_id={new_product.id}, user_id={user.id}")
        return jsonify({
            "success": True,
            "message": "Товар успешно добавлен",
            "product_id": new_product.id,
            "link_img": new_product.link_img
        }), 201

    except Exception as e:
        db.session.rollback()
        product_logger.exception(f"Критическая ошибка при добавлении товара от user_id={user.id}: {e}")
        return jsonify({"error": "Ошибка при добавлении товара в базу данных"}), 500


@api_bp.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    """
    Обновить существующий товар.
    Поддерживает:
      - application/json (тело с полями)
      - multipart/form-data (форма с изображением)
    """
    # Пользователь уже аутентифицирован и доступен через g (проверено в before_request)
    user = g.current_user

    product = db.session.get(Shop, id)
    if not product:
        product_logger.info(f"Попытка обновления несуществующего товара: product_id={id}, user_id={user.id}")
        return jsonify({"error": "Товар не найден"}), 404

    # Проверка прав доступа
    # Админ может обновлять любые товары. Продавец — только свои.
    if user.role != 'admin' and int(product.user_id) != g.current_user_id:
        product_logger.warning(f"Доступ запрещён: user_id={user.id} пытается обновить чужой товар product_id={id}")
        return jsonify({"error": "Товар не найден или недоступен"}), 404

    is_json = request.is_json

    if is_json:
        data = request.get_json() or {}
        image_file = None
    else:
        data = {}
        image_file = request.files.get('image')

    try:
        title = data.get('title') if is_json else request.form.get('title')
        if title is not None:
            title = title.strip()
            if not title:
                return jsonify({"error": "Название товара не может быть пустым"}), 400
            product.title = title

        description = data.get('description') if is_json else request.form.get('description')
        if description is not None:
            product.description = str(description).strip()

        category = data.get('category') if is_json else request.form.get('category')
        if category is not None:
            category = str(category).strip()
            if not category:
                return jsonify({"error": "Категория не может быть пустой"}), 400
            product.category = category

        article_num_input = data.get('article_num') if is_json else request.form.get('article_num')
        if article_num_input is not None:
            article_num_input = str(article_num_input).strip()
            if not article_num_input:
                return jsonify({"error": "Артикул не может быть пустым"}), 400
            existing = Shop.query.filter(
                Shop.article_num == article_num_input,
                Shop.id != id
            ).first()
            if existing:
                product_logger.warning(f"Попытка обновить товар до уже существующего артикула '{article_num_input}', product_id={id}")
                return jsonify({"error": "Товар с таким артикулом уже существует"}), 409
            product.article_num = article_num_input

        price_input = data.get('price') if is_json else request.form.get('price')
        if price_input is not None:
            try:
                price = float(price_input)
                if price < 0:
                    return jsonify({"error": "Цена не может быть отрицательной"}), 400
                product.price = price
            except (ValueError, TypeError):
                return jsonify({"error": "Цена должна быть числом"}), 400

        quantity_input = data.get('quantity') if is_json else request.form.get('quantity')
        if quantity_input is not None:
            try:
                quantity = int(quantity_input)
                if quantity < 0:
                    return jsonify({"error": "Количество не может быть отрицательным"}), 400
                product.quantity = quantity
            except (ValueError, TypeError):
                return jsonify({"error": "Количество должно быть целым числом"}), 400

        if is_json:
            sale_input = data.get('sale')
            if sale_input is not None:
                if isinstance(sale_input, bool):
                    product.sale = sale_input
                else:
                    return jsonify({"error": "Поле 'sale' должно быть булевым"}), 400
        else:
            product.sale = 'sale' in request.form

        if image_file and image_file.filename:
            try:
                product.link_img = save_product_image(image_file)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                product_logger.error(f"Ошибка загрузки изображения при обновлении product_id={id}: {e}")
                return jsonify({"error": "Ошибка при загрузке изображения"}), 500

        db.session.commit()
        product_logger.info(f"Товар успешно обновлён: product_id={id}, user_id={user.id}")
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
        product_logger.exception(f"Критическая ошибка при обновлении товара product_id={id} от user_id={user.id}: {e}")
        return jsonify({"error": "Ошибка при обновлении товара"}), 500


@api_bp.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    """
    Удалить товар по ID.
    - Админ может удалить любой товар.
    - Продавец — только свои. 
    """
    user = g.current_user
    product = db.session.get(Shop, id)
    if not product:
        product_logger.info(f"Попытка удаления несуществующего товара: product_id={id}, user_id={user}")
        return jsonify({"error": "Товар не найден"}), 404

    if user.role == 'suser' and int(product.user_id) != int(user.id):  # ← исправлено: user.id
        product_logger.warning(f"Доступ запрещён: user_id={user.id} пытается удалить чужой товар product_id={id}")
        return jsonify({"error": "Нет прав доступа. Вы можете удалять только свои товары."}), 403

    try:
        db.session.delete(product)
        db.session.commit()

        # Теперь безопасно удаляем файл
        if product.link_img:
            try:
                relative_path = product.link_img.lstrip("/")
                full_path = Path(current_app.static_folder) / relative_path
                if full_path.exists():
                    os.remove(full_path)
                    product_logger.info(f"Файл изображения удалён: {full_path}")
                else:
                    product_logger.warning(f"Файл изображения не найден при удалении товара: {full_path}")
            except Exception as e:
                product_logger.warning(f"Не удалось удалить файл изображения {product.link_img} для product_id={id}: {e}")

        product_logger.info(f"Товар успешно удалён: product_id={id}, user_id={user.id}")
        return jsonify({
            "success": True,
            "message": "Товар успешно удалён"
        }), 200

    except Exception as e:
        db.session.rollback()
        product_logger.exception(f"Критическая ошибка при удалении товара product_id={id} от user_id={user.id}: {e}")
        return jsonify({"error": "Ошибка при удалении товара"}), 500