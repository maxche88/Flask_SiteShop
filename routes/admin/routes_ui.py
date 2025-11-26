# Маршруты для пользователя с ролью admin.
from flask import Blueprint, render_template, g

admin_bp = Blueprint('panel_a', __name__)


@admin_bp.route('/admin_acaunt')
def admin_acaunt():
    return render_template('admin/admin_acaunt.html')


@admin_bp.route('/panel')
def admin_panel():
    user = g.current_user
    if user.role != 'admin':
        return "Доступ запрещён", 403
    return render_template('admin/admin_panel.html')