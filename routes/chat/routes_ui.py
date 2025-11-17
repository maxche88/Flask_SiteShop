from flask import Blueprint, render_template
from utils.user_sessions import get_safe_user_id
from models import User, MessageTopic

chat_ui_bp = Blueprint('chat_pages', __name__, url_prefix='/chat')

@chat_ui_bp.route('/send_mess')
def send_mess():
    """Универсальная форма для гостей и авторизованных."""
    user_id = get_safe_user_id()
    user = User.query.get(int(user_id)) if user_id else None
    topics = MessageTopic.query.filter_by(is_active=True).all()
    return render_template('send_message.html', user=user, topics=topics)


@chat_ui_bp.route('/send_mess_s')
def send_mess_s():
    """Страница сообщений для менеджеров (suser/admin)."""
    user_id = get_safe_user_id()
    if not user_id:
        return "Доступ запрещён", 403
    
    user = User.query.get(int(user_id))
    if user.role not in ('suser', 'admin'):
        return "Доступ запрещён", 403

    # Позже: список диалогов, фильтрация и т.д.
    return render_template('staff_messages.html', user=user)