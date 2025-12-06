from flask import Blueprint, render_template, g


user_bp = Blueprint('user', __name__, template_folder='templates')


@user_bp.route('/profile')
def profile():
    """
    Страница личного кабинета.
    Доступна всем авторизованным пользователям.
    """
    user = g.current_user

    context = {
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'pending_email': user.pending_email,
        'role': user.role,
        'confirm_email': user.confirm_email,
        'created_at': user.created_at,
    }

    return render_template('profile.html', **context)

