# Маршруты для пользователя с ролью admin.

from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User


admin_bp = Blueprint('panel_a', __name__)

@admin_bp.route('/admin_acaunt')
@jwt_required()
def admin_acaunt():
    return render_template('admin/admin_acaunt.html')

@admin_bp.route('/panel')
@jwt_required()
def admin_panel():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role not in 'admin':
        return "Доступ запрещён", 403
    return render_template('admin/admin_panel.html')