import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, CartItem, Shop, User, OrderItem, Order
from datetime import datetime, timezone


user_api_bp = Blueprint('user_api', __name__, url_prefix='/api/user')
order_logger = logging.getLogger('app.orders')


# === ДОБАВЛЕНИЕ В КОРЗИНУ ===
@user_api_bp.route('/cart', methods=['POST'])
@jwt_required()
def add_to_cart():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    product_id = request.form.get('product_id')
    if not product_id:
        return jsonify({"error": "Не указан ID товара"}), 400

    try:
        quantity = int(request.form.get('quantity', 1))
        if quantity < 1:
            quantity = 1
    except (TypeError, ValueError):
        quantity = 1

    product = Shop.query.get(product_id)
    if not product:
        return jsonify({"error": "Товар не найден"}), 404

    if quantity > product.quantity:
        quantity = product.quantity
    if quantity <= 0:
        return jsonify({"error": "Товара нет в наличии"}), 400

    cart_item = CartItem.query.filter_by(
        user_id=user.id,
        product_id=product.id
    ).first()

    if cart_item:
        new_total = cart_item.quantity + quantity
        if new_total > product.quantity:
            new_total = product.quantity
        if new_total <= 0:
            return jsonify({"error": "Товара нет в наличии"}), 400
        cart_item.quantity = new_total
    else:
        cart_item = CartItem(
            user_id=user.id,
            product_id=product.id,
            quantity=quantity,
            added_at=datetime.now(timezone.utc)
        )
        db.session.add(cart_item)
    
    db.session.commit()
    return jsonify({"success": True})


# === УДАЛЕНИЕ ИЗ КОРЗИНЫ ===
@user_api_bp.route('/cart', methods=['DELETE'])
@jwt_required()  # ← ОБЯЗАТЕЛЬНО!
def remove_from_cart():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    item_id = request.args.get('item_id')
    clear_all = request.args.get('clear') == 'all'

    if clear_all:
        CartItem.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        return jsonify({"success": True})

    elif item_id:
        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Некорректный ID элемента"}), 400

        cart_item = CartItem.query.filter_by(
            id=item_id,
            user_id=user.id
        ).first()
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Элемент не найден"}), 404
    else:
        return jsonify({"error": "Не указан ID элемента или флаг очистки"}), 400


# ОФОРМЛЕНИЕ ЗАКАЗА
@user_api_bp.route('/checkout', methods=['POST'])
@jwt_required()
def checkout():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        order_logger.warning(f"Попытка оформить заказ несуществующим пользователем: user_id={current_user_id}")
        return jsonify({"error": "Пользователь не найден"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Некорректное тело запроса"}), 400

    items_data = data.get('items')
    card_number = data.get('card_number')
    cardholder_name = data.get('cardholder_name')
    expiry = data.get('expiry')

    if not items_data or not isinstance(items_data, list) or len(items_data) == 0:
        return jsonify({"error": "Не выбрано ни одного товара"}), 400

    if not card_number or not cardholder_name or not expiry:
        return jsonify({"error": "Заполните все данные карты"}), 400

    # Преобразуем в словарь и валидируем
    client_quantities = {}
    for item in items_data:
        item_id = item.get('item_id')
        qty = item.get('quantity')
        if not isinstance(item_id, int) or not isinstance(qty, int) or qty < 1:
            return jsonify({"error": "Некорректные данные товара"}), 400
        client_quantities[item_id] = qty

    # Загружаем соответствующие записи корзины
    cart_items = CartItem.query.filter(
        CartItem.id.in_(list(client_quantities.keys())),
        CartItem.user_id == user.id
    ).all()

    if len(cart_items) != len(client_quantities):
        order_logger.warning(f"Попытка оформить заказ с чужими/несуществующими товарами: user_id={user.id}, item_ids={list(client_quantities.keys())}")
        return jsonify({"error": "Некоторые товары не найдены в корзине"}), 400

    # Проверка остатков с учётом КОЛИЧЕСТВА от клиента
    errors = []
    total_amount = 0
    for item in cart_items:
        requested_qty = client_quantities[item.id]
        product = item.product
        if not product:
            errors.append(f"Товар с ID {item.product_id} удалён.")
            continue
        if requested_qty > product.quantity:
            errors.append(f"Товара «{product.title}» нет в таком количестве. На складе всего {product.quantity} шт.")
        total_amount += product.price * requested_qty

    if errors:
        return jsonify({"error": "Невозможно оформить заказ", "details": errors}), 400

    # Создание заказа
    try:
        order = Order(
            user_id=user.id,
            total_amount=total_amount,
            card_number=card_number[-4:],
            cardholder_name=cardholder_name,
            expiry=expiry
        )
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            requested_qty = client_quantities[item.id]
            product = item.product

            # Повторная проверка
            if requested_qty > product.quantity:
                db.session.rollback()
                return jsonify({"error": f"Товар «{product.title}» закончился. Попробуйте обновить страницу."}), 409

            product.quantity -= requested_qty
            if product.quantity < 0:
                product.quantity = 0

            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=requested_qty,
                price_at_purchase=product.price
            )
            db.session.add(order_item)
            db.session.delete(item)

        db.session.commit()
        order_logger.info(f"Заказ успешно оформлен: order_id={order.id}, user_id={user.id}, сумма={total_amount}")
        return jsonify({"success": True, "message": "Заказ успешно оформлен", "order_id": order.id})

    except Exception as e:
        db.session.rollback()
        order_logger.exception(f"Критическая ошибка при оформлении заказа: user_id={user.id}")
        return jsonify({"error": "Ошибка при создании заказа"}), 500

@user_api_bp.route('/cart/count')
@jwt_required()
def cart_count():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"count": 0}), 404

    total_quantity = db.session.query(db.func.sum(CartItem.quantity)) \
        .filter_by(user_id=user.id) \
        .scalar() or 0

    return jsonify({"count": int(total_quantity)})