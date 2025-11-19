from flask import Blueprint, request, jsonify
from extensions import db
from models import Dialog, Message, User, MessageTopic
from services.chat_service import create_guest_dialog, create_user_dialog
from utils.mail import send_guest_dialog_reply
from utils.user_sessions import get_safe_user_id
import logging
import re
from sqlalchemy import func

chat_bp = Blueprint('chat_api', __name__, url_prefix='/api/chat')
chat_logger = logging.getLogger('app.chat')


@chat_bp.route('/topics', methods=['GET'])
def get_message_topics():
    """Возвращает список активных тем обращений. Доступен без авторизации."""
    topics = MessageTopic.query.filter_by(is_active=True).order_by(MessageTopic.name).all()

    return jsonify([
        {'id': topic.id, 'name': topic.name}
        for topic in topics
    ]), 200


@chat_bp.route('/dialogs', methods=['POST'])
def create_dialog_api():
    """
    Универсальный эндпоинт для создания диалога:
    Гости: передают name, email
    Авторизованные (user): данные берутся из JWT
    suser/admin: запрещены
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'errors': ['Ожидается JSON.']}), 400

    # Определяем пользователя
    user_id_str = get_safe_user_id()
    current_user = None
    is_guest = user_id_str is None

    if not is_guest:
        try:
            user_id = int(user_id_str)
            current_user = User.query.get(user_id)
            if not current_user:
                return jsonify({'success': False, 'errors': ['Пользователь не найден.']}), 404
            if current_user.role in ('suser', 'admin'):
                return jsonify({'success': False, 'errors': ['Администраторы не могут создавать диалоги через этот интерфейс.']}), 403
        except (TypeError, ValueError):
            return jsonify({'success': False, 'errors': ['Некорректный идентификатор пользователя.']}), 400

    # Общие данные
    text = data.get('text', '').strip()
    product_id = data.get('product_id')
    order_id = data.get('order_id')
    context = data.get('context')

    errors = []

    if not text:
        errors.append('Текст сообщения обязателен.')
    elif len(text) > 300:
        errors.append('Сообщение не должно превышать 300 символов.')

    if product_id is not None:
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            errors.append('Некорректный ID товара.')

    if order_id is not None:
        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            errors.append('Некорректный ID заказа.')

    # Данные отправителя
    guest_name = None
    guest_email = None

    if is_guest:
        guest_name = data.get('guest_name', '').strip()
        guest_email = data.get('guest_email', '').strip()
        if not guest_name:
            errors.append('Имя обязательно.')
        if not guest_email:
            errors.append('Email обязателен.')
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', guest_email):
            errors.append('Некорректный email.')


    # Категория (topic_id)
    topic_id = None
    if context == 'product_question':
        topic_id = 1  # Фиксированный ID темы "Вопрос о товаре"
        topic = MessageTopic.query.filter_by(id=topic_id, is_active=True).first()
        if not topic:
            errors.append('Тема обращения недоступна.')
    else:
        topic_id = data.get('topic_id')
        if topic_id is None:
            errors.append('Тема обращения обязательна.')
        elif not isinstance(topic_id, int):
            errors.append('Некорректный ID темы.')
        else:
            topic = MessageTopic.query.filter_by(id=topic_id, is_active=True).first()
            if not topic:
                errors.append('Тема недоступна.')

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    # Создание диалога
    try:
        if current_user:
            dialog = create_user_dialog(
                user_id=current_user.id,
                topic_id=topic_id,
                text=text,
                product_id=product_id,
                order_id=order_id
            )

        else:
            dialog = create_guest_dialog(
                guest_name=guest_name,
                guest_email=guest_email,
                topic_id=topic_id,
                text=text,
                product_id=product_id,
                order_id=order_id
            )

        return jsonify({
            'success': True,
            'message': 'Ваше обращение отправлено.',
            'dialog_id': dialog.id
        }), 201

    except ValueError as e:
        db.session.rollback()
        chat_logger.error(f"Ошибка валидации при создании диалога: {e}")
        return jsonify({'success': False, 'errors': [str(e)]}), 400

    except Exception as e:
        db.session.rollback()
        chat_logger.exception("Неожиданная ошибка при создании диалога")
        return jsonify({'success': False, 'errors': ['Внутренняя ошибка сервера.']}), 500


@chat_bp.route('/dialogs', methods=['GET'])
def get_all_dialogs():
    """
    Возвращает полный список диалогов для панели поддержки.
    
    Требования:
      - Авторизация обязательна (JWT).
      - Доступ разрешён только ролям 'suser' (менеджер) и 'admin'.
    
    Особенности ответа:
      - Для каждого диалога возвращаются контактные данные (name, email),
        даже если это зарегистрированный пользователь.
      - Дополнительно указывается user_id (если есть) и username из профиля.
      - Подсчитывается общее число сообщений и определяется роль последнего отправителя.
    
    ВАЖНО: 
      Этот эндпоинт может быть тяжёлым при большом числе диалогов.
      В будущем рекомендуется добавить постраничную навигацию (пагинацию).
    
    Returns:
        JSON: список диалогов с полями:
          - id, user_id, name, email, topic_name, username,
          - order_id, product_id, status, updated_at,
          - message_count, last_sender_role
    """
    # Проверка авторизации
    current_user_id = get_safe_user_id()
    if not current_user_id:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        chat_logger.error("Получен некорректный user_id при запросе списка диалогов")
        return jsonify({'error': 'Некорректный идентификатор пользователя'}), 400

    # Проверка роли
    user = User.query.get(current_user_id)
    if not user or user.role not in ('suser', 'admin'):
        chat_logger.warning(
            f"Попытка доступа к списку диалогов от недопустимой роли: "
            f"{user.role if user else 'None'} (user_id={current_user_id})"
        )
        return jsonify({'error': 'Доступ запрещён'}), 403

    # Загрузка диалогов с предзагрузкой связанных данных
    try:
        # Загружаем все диалоги, сортируя по актуальности
        dialogs = Dialog.query.order_by(Dialog.updated_at.desc()).all()

        result = []
        for dialog in dialogs:
            # Оптимизируем подсчёт сообщений и получение последнего отправителя
            messages_query = Message.query.filter_by(dialog_id=dialog.id)
            message_count = messages_query.count()
            
            last_message = messages_query.order_by(Message.created_at.desc()).first()
            last_sender_role = last_message.sender_role if last_message else None

            result.append({
                'id': dialog.id,
                'user_id': dialog.user_id,  # None для гостей
                'name': dialog.name,        # всегда заполнено (и для гостей, и для пользователей)
                'email': dialog.email,      # всегда заполнено
                'username': dialog.user.username if dialog.user else None,  # только для зарегистрированных
                'topic_name': dialog.topic.name if dialog.topic else '—',
                'order_id': dialog.order_id,
                'product_id': dialog.product_id,
                'status': dialog.status,
                'updated_at': dialog.updated_at.isoformat() if dialog.updated_at else None,
                'message_count': message_count,
                'last_sender_role': last_sender_role
            })

        return jsonify(result), 200

    except Exception as e:
        chat_logger.exception("Критическая ошибка при загрузке списка диалогов")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@chat_bp.route('/dialogs/<int:dialog_id>/messages', methods=['GET'])
def get_dialog_messages(dialog_id):
    """
    Возвращает все сообщения в указанном диалоге.
    
    Доступ: только для авторизованных suser/admin.
    Проверяет:
      - существование диалога (404, если не найден),
      - права доступа (403, если роль не разрешена).
    
    Args:
        dialog_id (int): ID диалога

    Returns:
        JSON: список сообщений с полями id, sender_role, text, created_at
    """
    current_user_id = get_safe_user_id()
    if not current_user_id:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        chat_logger.error(f"Некорректный ID пользователя при запросе сообщений диалога {dialog_id}")
        return jsonify({'error': 'Некорректный идентификатор пользователя'}), 400

    user = User.query.get(current_user_id)
    if not user or user.role not in ('suser', 'admin'):
        chat_logger.warning(f"Попытка доступа к диалогу {dialog_id} от недопустимой роли: {user.role if user else 'None'}")
        return jsonify({'error': 'Доступ запрещён'}), 403

    try:
        # Проверяем существование диалога (404 если не найден)
        dialog = Dialog.query.get(dialog_id)
        if not dialog:
            return jsonify({'error': 'Диалог не найден'}), 404

        messages = Message.query.filter_by(
            dialog_id=dialog_id
        ).order_by(
            Message.created_at.asc()
        ).all()

        return jsonify([{
            'id': msg.id,
            'sender_role': msg.sender_role,
            'text': msg.text,
            'created_at': msg.created_at.isoformat()
        } for msg in messages]), 200

    except Exception as e:
        chat_logger.exception(f"Ошибка при загрузке сообщений диалога {dialog_id}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@chat_bp.route('/dialogs/<int:dialog_id>/reply', methods=['POST'])
def send_reply_to_dialog(dialog_id):
    """
    Отправляет ответ от менеджера или администратора в существующий диалог.
    
    Требования:
      - Авторизация обязательна (JWT).
      - Только роли 'suser' (менеджер) и 'admin' могут отвечать.
      - Диалог должен существовать и иметь статус 'open'.
    
    Особенности:
      - Если диалог инициирован гостем (user_id IS NULL), 
        ответ дополнительно отправляется на email гостя.
      - Для зарегистрированных пользователей уведомление 
        доставляется только через внутреннюю систему сообщений.
    
    Args:
        dialog_id (int): ID диалога, в который отправляется ответ.

    Request JSON:
        {
            "text": "Текст ответа (1–300 символов)"
        }

    Returns:
        JSON:
        - Успех (201): { "success": true, "message_id": N, "sent_at": ISO8601 }
        - Ошибки (400/401/403/404): { "error": "сообщение" }
    """
    # Проверка авторизации
    current_user_id = get_safe_user_id()
    if not current_user_id:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        chat_logger.error(f"Некорректный ID пользователя при попытке ответа в диалог {dialog_id}")
        return jsonify({'error': 'Некорректный идентификатор пользователя'}), 400

    # Проверка роли
    user = User.query.get(current_user_id)
    if not user or user.role not in ('suser', 'admin'):
        chat_logger.warning(
            f"Попытка отправить ответ в диалог {dialog_id} от недопустимой роли: "
            f"{user.role if user else 'None'} (user_id={current_user_id})"
        )
        return jsonify({'error': 'Доступ запрещён'}), 403

    # Проверка существования и статуса диалога
    dialog = Dialog.query.get(dialog_id)
    if not dialog:
        return jsonify({'error': 'Диалог не найден'}), 404

    if dialog.status != 'open':
        return jsonify({'error': 'Нельзя отвечать в закрытый диалог'}), 400

    # Валидация входных данных
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Ожидается JSON'}), 400

    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400

    # Сохранение сообщения и отправка уведомлений
    try:
        # Создаём новое сообщение от админа/менеджера
        new_message = Message(
            dialog_id=dialog_id,
            sender_user_id=current_user_id,
            sender_role=user.role,
            text=text
        )
        db.session.add(new_message)
        dialog.updated_at = func.now()  # Обновляем время последней активности
        db.session.commit()

        # Если диалог от гостя — отправляем email
        if dialog.user_id is None:
            email_sent = send_guest_dialog_reply(
                dialog_id=dialog.id,
                guest_name=dialog.name,
                guest_email=dialog.email,
                reply_text=text,
                sender_role=user.role
            )
            if not email_sent:
                chat_logger.warning(f"Не удалось отправить email гостю в диалоге {dialog.id}")

        # Успешный ответ
        return jsonify({
            'success': True,
            'message_id': new_message.id,
            'sent_at': new_message.created_at.isoformat()
        }), 201

    except Exception as e:
        # Откат транзакции при любой ошибке
        db.session.rollback()
        chat_logger.exception(f"Критическая ошибка при отправке ответа в диалог {dialog_id}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500