from flask import Blueprint, render_template, g
from models import CartItem, Order, OrderItem
from extensions import db


user_ui_bp = Blueprint('user_ui', __name__, url_prefix='/user')


# Страница управления акаунтом.
@user_ui_bp.route('/user_accaunt')
def user_accaunt():
    return render_template('user/user_accaunt.html')


@user_ui_bp.route('/orders')
def user_order():
    user_id = g.current_user_id

    # Загружаем все купленные товары пользователя
    order_items = db.session.query(OrderItem)\
        .join(Order, Order.id == OrderItem.order_id)\
        .filter(Order.user_id == user_id)\
        .order_by(Order.created_at.desc())\
        .all()

    return render_template('user/user_order.html', order_items=order_items)


@user_ui_bp.route('/cart')
def cart_page():
    user = g.current_user

    cart_items = CartItem.query.filter_by(user_id=user.id).all()
    return render_template('user/cart.html', cart_items=cart_items)