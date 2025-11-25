# Маршруты для пользователя с ролью suser.
from flask import Blueprint, render_template



staff_bp = Blueprint('panel_s', __name__)

# Страница управления акаунтом.
@staff_bp.route('/suser_acaunt')
def suser_panel_acaunt():
    return render_template('staff/suser_acaunt.html')