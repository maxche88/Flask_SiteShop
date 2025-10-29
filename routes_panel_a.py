# Маршруты для пользователя с ролью admin.

from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required


admin_bp = Blueprint('panel_a', __name__)

@admin_bp.route('/admin_acaunt')
@jwt_required()
def admin_acaunt():
    return render_template('admin_acaunt.html')

@admin_bp.route('/admin_panel')
@jwt_required()
def admin_panel():
    return render_template('admin_panel.html')