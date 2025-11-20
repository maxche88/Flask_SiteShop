from flask import Blueprint, render_template
from utils.user_sessions import get_safe_user_id
from models import User, Dialog

chat_ui_bp = Blueprint('chat_ui', __name__, url_prefix='/chat')


@chat_ui_bp.route('/messages_panel')
def messages_panel():
    """Страница сообщений для менеджеров (suser/admin)."""
    user_id = get_safe_user_id()
    if not user_id:
        return "Доступ запрещён", 403
    
    user = User.query.get(int(user_id))
    if not user or user.role not in ('suser', 'admin'):
        return "Доступ запрещён", 403

    return render_template(
        'messages_panel.html',
        user_id=user.id,
        role=user.role
    )

@chat_ui_bp.route('/my_messages')
def my_messages():
    """
    Страница личных сообщений для авторизованного пользователя (роль 'user').
    """
    user_id = get_safe_user_id()
    if not user_id:
        return "Доступ запрещён", 403

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return "Некорректный идентификатор пользователя", 400

    user = User.query.get(user_id)
    if not user or user.role != 'user':
        return "Доступ запрещён", 403

    return render_template(
        'user/user_messages.html',
        user_id=user.id,
        role=user.role
    )