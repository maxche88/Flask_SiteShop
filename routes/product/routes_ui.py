# Маршруты для пользователя с ролью suser.
from flask import Blueprint, render_template, redirect, url_for, g
from models import Shop
from extensions import db


product_bp = Blueprint('product_edit', __name__)


# Страница управления товарами.
@product_bp.route('/product')
def product():
    user = g.current_user
    
    if user.role not in ('suser', 'admin'):
        return redirect(url_for('session.login'))
    
    return render_template('product/edit_product_panel.html',
                         user_id=g.current_user_id,
                         role=user.role)

# Форма добавления товара.
@product_bp.route('/add-product')
def add_product():
    # Доступ уже проверен в before_request, но проверим роль
    if g.current_user.role not in ('suser', 'admin'):
        return redirect(url_for('session.login'))
    return render_template('product/add_product.html')

# Форма редактирования товара. 
@product_bp.route('/edit-product/<int:product_id>')
def edit_product(product_id):
    user = g.current_user

    product = db.session.get(Shop, product_id)
    if not product:
        return render_template('404.html'), 404

    # Проверка прав доступа
    # Админ может редактировать и видеть все товары. suser — только свои товары.
    if user.role != 'admin' and int(product.user_id) != g.current_user_id:
        return render_template(
            'error.html',
            message="Нет прав доступа. Вы можете редактировать только свои товары."
        ), 403

    return render_template('product/edit_product_form.html', product=product)