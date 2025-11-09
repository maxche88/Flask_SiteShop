from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, CartItem, Shop, User, current_time
from utils.logger import get_user_logger

user_api_bp = Blueprint('user_api', __name__, url_prefix='/api/user')


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
        product_id=product.id,
        is_purchased=False
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
            is_purchased=False,
            added_at=current_time()
        )
        db.session.add(cart_item)
    
    db.session.commit()

    return jsonify({"success": True})


@user_api_bp.route('/cart', methods=['DELETE'])
@jwt_required()
def remove_from_cart():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    item_id = request.args.get('item_id')
    clear_all = request.args.get('clear') == 'all'

    if clear_all:
        CartItem.query.filter_by(user_id=user.id, is_purchased=False).delete()
        db.session.commit()
        return jsonify({"success": True})

    elif item_id:
        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Некорректный ID элемента"}), 400

        cart_item = CartItem.query.filter_by(
            id=item_id,
            user_id=user.id,
            is_purchased=False
        ).first()
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Элемент не найден"}), 404
    else:
        return jsonify({"error": "Не указан ID элемента или флаг очистки"}), 400


@user_api_bp.route('/checkout', methods=['POST'])
@jwt_required()
def checkout():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    cart_items = CartItem.query.filter_by(user_id=user.id, is_purchased=False).all()
    if not cart_items:
        return jsonify({"error": "Корзина пуста"}), 400

    errors = []
    for item in cart_items:
        product = Shop.query.get(item.product_id)
        if not product:
            errors.append(f"Товар с ID {item.product_id} удалён из каталога.")
            continue
        if item.quantity < 1:
            errors.append(f"Некорректное количество для товара «{product.title}».")
        elif item.quantity > product.quantity:
            errors.append(
                f"Товара «{product.title}» осталось только {product.quantity} шт., "
                f"а у вас в корзине {item.quantity}."
            )

    if errors:
        return jsonify({"error": "Невозможно оформить заказ", "details": errors}), 400

    for item in cart_items:
        product = Shop.query.get(item.product_id)
        product.quantity -= item.quantity
        if product.quantity < 0:
            product.quantity = 0
        item.is_purchased = True
        item.purchased_at = current_time()

    db.session.commit()
    return jsonify({"success": True, "message": "Заказ успешно оформлен"})


@user_api_bp.route('/cart/count')
@jwt_required()
def cart_count():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"count": 0}), 404

    total_quantity = db.session.query(db.func.sum(CartItem.quantity)) \
        .filter_by(user_id=user.id, is_purchased=False) \
        .scalar() or 0

    return jsonify({"count": int(total_quantity)})