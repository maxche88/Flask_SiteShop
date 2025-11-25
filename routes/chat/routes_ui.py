from flask import Blueprint, render_template, g

chat_ui_bp = Blueprint('chat_ui', __name__, url_prefix='/chat')


@chat_ui_bp.route('/messages_panel')
def messages_panel():
    """Страница сообщений для менеджеров (suser/admin)."""
    user = g.current_user
    if user.role not in ('suser', 'admin'):
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
    user = g.current_user
    if user.role != 'user':
        return "Доступ запрещён", 403

    return render_template(
        'user/user_messages.html',
        user_id=user.id,
        role=user.role
    )