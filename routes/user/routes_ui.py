from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import CartItem, User


user_ui_bp = Blueprint('user_ui', __name__, url_prefix='/user')


# Страница управления акаунтом.
@user_ui_bp.route('/user_accaunt')
@jwt_required()
def user_accaunt():
    return render_template('user/user_accaunt.html')


@user_ui_bp.route('/cart')
@jwt_required()
def cart_page():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        # В UI лучше перенаправить на логин, но пока оставим простой ответ
        return "Пользователь не найден", 404

    cart_items = CartItem.query.filter_by(
        user_id=user.id,
        is_purchased=False
    ).all()
    return render_template('user/cart.html', cart_items=cart_items)
