# Маршруты для пользователя с ролью super user.

from flask import Blueprint, render_template, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, Shop


product_bp = Blueprint('product_edit', __name__)


# Страница управления товарами.
@product_bp.route('/product')
@jwt_required()
def product():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return redirect(url_for('session.login'))  # или 404
    
    if user.role not in ('suser', 'admin'):
        return redirect(url_for('session.login'))
    
    return render_template('product/edit_product_panel.html',
                         user_id=current_user_id,
                         role=user.role)

# Форма добавления товара.
@product_bp.route('/add-product')
@jwt_required()
def add_product():
    return render_template('product/add_product.html')

# Форма редактирования товара.
@product_bp.route('/edit-product/<int:product_id>')
@jwt_required()
def edit_product(product_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return render_template('404.html'), 404

    product = Shop.query.get(product_id)
    if not product:
        return render_template('404.html'), 404

    # Проверка прав доступа
    # Админ может редактировать всё. Staff — только свои товары.
    if user.role != 'admin' and int(product.user_id) != int(current_user_id):
        return render_template(
            'error.html',
            message="Нет прав доступа. Вы можете редактировать только свои товары."
        ), 403

    return render_template('product/edit_product_form.html', product=product)