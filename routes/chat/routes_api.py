from flask import Blueprint, request, jsonify
from models import MessageTopic, db
import logging

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')
chat_logger = logging.getLogger('chat')



# Роуты для гостевого обращения
@chat_bp.route('/topics', methods=['GET'])
def get_message_topics():
    """
    Возвращает список активных тем обращений.
    Доступен без авторизации.
    """
    topics = MessageTopic.query.filter_by(is_active=True).order_by(MessageTopic.name).all()
    return jsonify([
        {'id': topic.id, 'name': topic.name}
        for topic in topics
    ]), 200


@chat_bp.route('/guest-dialogs', methods=['POST'])
def create_guest_dialog_api():
    """
    Создаёт новый диалог от гостя.
    Требует: guest_name, guest_email, topic_id, text.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'errors': ['Неверный формат данных (ожидается JSON).']}), 400

    import re
    def is_valid_email(email):
        return re.match(r'^[^@]+@[^@]+\.[^@]+$', email.strip()) is not None

    errors = []
    guest_name = data.get('guest_name', '').strip()
    guest_email = data.get('guest_email', '').strip()
    topic_id = data.get('topic_id')
    text = data.get('text', '').strip()

    if not guest_name:
        errors.append('Имя обязательно для заполнения.')
    if not guest_email:
        errors.append('Email обязателен для заполнения.')
    elif not is_valid_email(guest_email):
        errors.append('Указан некорректный email.')
    if topic_id is None:
        errors.append('Тема обращения обязательна.')
    elif not isinstance(topic_id, int):
        errors.append('Некорректный идентификатор темы.')
    if not text:
        errors.append('Текст сообщения обязателен.')
    elif len(text) > 300:
        errors.append('Сообщение не должно превышать 300 символов.')

    if not errors:
        topic = MessageTopic.query.filter_by(id=topic_id, is_active=True).first()
        if not topic:
            errors.append('Выбрана недопустимая тема обращения.')

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    try:
        from services.chat_service import create_guest_dialog
        dialog = create_guest_dialog(
            guest_name=guest_name,
            guest_email=guest_email.lower().strip(),
            topic_id=topic_id,
            text=text,
            product_id=data.get('product_id'),
            order_id=data.get('order_id')
        )
        return jsonify({
            'success': True,
            'dialog_id': dialog.id,
            'message': 'Ваше обращение отправлено. Ответ придёт на указанный email.'
        }), 201

    except Exception as e:
        db.session.rollback()
        chat_logger.exception("Ошибка при создании гостевого диалога")
        return jsonify({'success': False, 'errors': ['Ошибка при создании обращения.']}), 500