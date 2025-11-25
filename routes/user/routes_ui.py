from flask_jwt_extended import unset_jwt_cookies
from flask import Blueprint, render_template, make_response, redirect, url_for
from utils.user_sessions import get_safe_user_id
from models import db, CartItem, User, Order, OrderItem


user_ui_bp = Blueprint('user_ui', __name__, url_prefix='/user')


# Страница управления акаунтом.
@user_ui_bp.route('/user_accaunt')
def user_accaunt():
    user_id_or_signal = get_safe_user_id()

    # Если токен недействителен — очищаем и редиректим
    if user_id_or_signal == "CLEAR_COOKIE":
        response = make_response(redirect(url_for('session.login')))
        # response.set_cookie('access_token', '', expires=0)
        unset_jwt_cookies(response)
        return response

    # Если пользователь не авторизован — редирект на логин
    if user_id_or_signal is None:
        return redirect(url_for('session.login'))

    # Пользователь авторизован — показываем страницу
    return render_template('user/user_accaunt.html')


@user_ui_bp.route('/orders')
def user_order():
    user_id_or_signal = get_safe_user_id()

    # Если токен недействителен — очищаем и редиректим
    if user_id_or_signal == "CLEAR_COOKIE":
        response = make_response(redirect(url_for('session.login')))
        # response.set_cookie('access_token', '', expires=0)
        unset_jwt_cookies(response)
        return response

    # Если пользователь не авторизован — редирект на логин
    if user_id_or_signal is None:
        return redirect(url_for('session.login'))

    # Получаем ID как целое число
    try:
        user_id = int(user_id_or_signal)
    except (TypeError, ValueError):
        return redirect(url_for('session.login'))

    # Загружаем все купленные товары пользователя
    order_items = db.session.query(OrderItem)\
        .join(Order, Order.id == OrderItem.order_id)\
        .filter(Order.user_id == user_id)\
        .order_by(Order.created_at.desc())\
        .all()

    return render_template('user/user_order.html', order_items=order_items)


@user_ui_bp.route('/cart')
def cart_page():
    user_id_or_signal = get_safe_user_id()

    if user_id_or_signal == "CLEAR_COOKIE":
        response = make_response(redirect(url_for('session.login')))
        # response.set_cookie('access_token', '', expires=0)
        unset_jwt_cookies(response)
        return response

    if user_id_or_signal is None:
        return redirect(url_for('session.login'))

    try:
        user_id = int(user_id_or_signal)
    except (TypeError, ValueError):
        return redirect(url_for('session.login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('session.login'))

    cart_items = CartItem.query.filter_by(user_id=user.id).all()
    return render_template('user/cart.html', cart_items=cart_items)
