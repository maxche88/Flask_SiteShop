from flask import Blueprint, render_template
from flask_jwt_extended import get_jwt_identity, jwt_required
from models import User, Shop


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@jwt_required(optional=True)
def index():
    """Отображает главную страницу интернет-магазина.

    Маршрут доступен как анонимным пользователям, так и авторизованным.
    Если пользователь авторизован (имеет валидный JWT в cookie),
    в шаблон передаются его имя и роль. Иначе отображается как «Гость».

    Returns:
        Response: HTML-страница 'index.html' с контекстом:
            - username (str): имя пользователя или "Гость"
            - role (str or None): роль пользователя или None
    """

    # Базовый контекст для "Гостя"
    context = {
        "username": "Гость",
        "role": None
    }

    current_user_id = get_jwt_identity()  # Вернёт user_id, если токен валиден; иначе — None
    if current_user_id is not None:
        user = User.query.get(current_user_id)
        if user:
            context.update({
                "гuserid": current_user_id,
                "username": user.username,
                "role": user.role,
            })

    return render_template('index.html', **context)


@main_bp.route('/product/<int:product_id>')
@jwt_required(optional=True)
def product_page(product_id):
    """Отображает страницу отдельного товара по его ID.

    Маршрут доступен всем. Если пользователь авторизован — в шаблон
    передаются его имя и роль. Товар загружается из базы по product_id.
    Если товар не найден — возвращается страница 404.

    Args:
        product_id (int): Уникальный идентификатор товара в базе данных.

    Returns:
        Response: 
            - HTML-страница 'view_product.html' с контекстом:
                * product (Shop): объект товара
                * username (str or None): имя пользователя или None
                * role (str or None): роль пользователя или None
            - ИЛИ страница '404.html' с HTTP-статусом 404, если товар не найден.
    """
    product = Shop.query.get(product_id)  # Получаем товар
    if not product:
        return render_template('404.html'), 404

    # Базовый контекст для "Гостя"
    context = {
        "username": None,
        "role": None,
    }

    current_user_id = get_jwt_identity()  # вернёт None, если токена нет или он невалиден
    if current_user_id is not None:
        user = User.query.filter_by(id=current_user_id).first()
        if user:
            context.update({
                "username": user.username,
                "role": user.role,
            })

    return render_template('view_product.html', product=product, **context)
