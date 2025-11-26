from flask import Blueprint, render_template, make_response
from flask_jwt_extended import unset_jwt_cookies
from utils.user_sessions import get_safe_user_id
from models import User, Shop
from extensions import db


main_bp = Blueprint('main', __name__)



@main_bp.route('/')
def index():
    user_id = get_safe_user_id()

    if user_id is None:
        response = make_response(render_template('index.html', username="Гость", role=None))
        unset_jwt_cookies(response)
        return response

    # Пользователь авторизован
    user = db.session.get(User, int(user_id))
    context = {
        "username": user.username if user else "Гость",
        "role": user.role if user else None
    }

    return render_template('index.html', **context)


@main_bp.route('/product/<int:product_id>')
def product_page(product_id):
    """
    Страница товара. Безопасно обрабатывает JWT-токен:
    - если токен валиден — показывает данные пользователя,
    - если токен недействителен или отсутствует — очищает куку и показывает как гостя.
    """
    product = db.session.get(Shop, product_id)
    if not product:
        return render_template('404.html'), 404

    # Получаем user_id или None (если токен недействителен/отсутствует)
    user_id = get_safe_user_id()

    # Если нет валидной сессии — всегда очищаем куку и показываем как гостя
    if user_id is None:
        response = make_response(render_template('view_product.html', product=product, username=None, role=None))
        unset_jwt_cookies(response)
        return response

    # Пользователь авторизован — подгружаем его данные
    user = db.session.get(User, int(user_id))
    context = {
        "username": user.username if user else None,
        "role": user.role if user else None
    }

    return render_template('view_product.html', product=product, **context)