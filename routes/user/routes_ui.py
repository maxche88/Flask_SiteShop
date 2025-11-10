from flask import Blueprint, render_template, make_response, redirect, url_for
from utils.user_sessions import get_safe_user_id
from models import CartItem, User


user_ui_bp = Blueprint('user_ui', __name__, url_prefix='/user')


# Страница управления акаунтом.
@user_ui_bp.route('/user_accaunt')

def user_accaunt():
    user_id_or_signal = get_safe_user_id()

    # Если токен недействителен — очищаем и редиректим
    if user_id_or_signal == "CLEAR_COOKIE":
        response = make_response(redirect(url_for('session.login')))
        response.set_cookie('access_token_cookie', '', expires=0)
        return response

    # Если пользователь не авторизован — редирект на логин
    if user_id_or_signal is None:
        return redirect(url_for('session.login'))

    # Пользователь авторизован — показываем страницу
    return render_template('user/user_accaunt.html')


@user_ui_bp.route('/cart')

def cart_page():
    user_id = get_safe_user_id()

    if user_id is None:
        response = make_response(redirect(url_for('session.login')))
        response.set_cookie('access_token', '', expires=0)
        return response

    user = User.query.get(int(user_id))
    if not user:
        return redirect(url_for('session.login'))

    cart_items = CartItem.query.filter_by(user_id=user.id, is_purchased=False).all()
    return render_template('user/cart.html', cart_items=cart_items)
