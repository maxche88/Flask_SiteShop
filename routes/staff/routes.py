# Маршруты для пользователя с ролью suser.

from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required


staff_bp = Blueprint('panel_s', __name__)

# Страница управления акаунтом.
@staff_bp.route('/suser_acaunt')
@jwt_required()
def suser_panel_acaunt():
    return render_template('staff/suser_acaunt.html')