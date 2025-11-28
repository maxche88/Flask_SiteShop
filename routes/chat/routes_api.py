from flask import Blueprint, request, jsonify, g
from extensions import db
from models import Dialog, Message, User, MessageTopic
from services.chat_service import create_guest_dialog, create_user_dialog, send_message_in_dialog
from utils.mail import send_guest_dialog_reply, normalize_email
from utils.user_sessions import get_safe_user_id
import logging
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


@chat_bp.route('/unread-count', methods=['GET'])
def get_unread_message_count():
    """
    Возвращает количество непрочитанных сообщений для ТЕКУЩЕГО пользователя
    ТОЛЬКО в диалогах со статусом 'open'.
    
    - Для 'user': непрочитанные сообщения от поддержки.
    - Для 'suser'/'admin': непрочитанные сообщения от пользователей.
    """
    user = g.current_user

    try:
        if user.role == 'user':
            count = db.session.query(Message).join(Dialog).filter(
                Dialog.user_id == user.id,
                Dialog.status == 'open',
                Message.sender_role.in_(['suser', 'admin']),
                Message.is_read == False
            ).count()

        elif user.role in ('suser', 'admin'):
            count = db.session.query(Message).join(Dialog).filter(
                Dialog.status == 'open',
                Message.sender_role.in_(['user', 'guest']),
                Message.is_read == False
            ).count()

        else:
            count = 0

        return jsonify({'unread_count': count}), 200

    except Exception as e:
        chat_logger.exception("Ошибка при подсчёте непрочитанных сообщений")
        return jsonify({'unread_count': 0}), 200


@chat_bp.route('/dialogs/guest', methods=['POST'])
def create_guest_dialog_api():
    """
    Создать диалог от гостя.
    Доступен без авторизации.
    Требует: guest_name, guest_email, text, topic_id (или context='product_question')
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'errors': ['Ожидается JSON.']}), 400

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

    # Данные гостя
    guest_name = data.get('guest_name', '').strip()
    raw_guest_email = data.get('guest_email', '').strip()
    if not guest_name:
        errors.append('Имя обязательно.')
    if not raw_guest_email:
        errors.append('Email обязателен.')
    else:
        normalized_email = normalize_email(raw_guest_email)
        if normalized_email is None:
            errors.append('Некорректный email.')
        else:
            guest_email = normalized_email

    # Определение темы
    topic_id = None
    if context == 'product_question':
        topic_id = 1
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

    try:
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
        chat_logger.error(f"Ошибка валидации при создании диалога гостем: {e}")
        return jsonify({'success': False, 'errors': [str(e)]}), 400

    except Exception as e:
        db.session.rollback()
        chat_logger.exception("Неожиданная ошибка при создании диалога гостем")
        return jsonify({'success': False, 'errors': ['Внутренняя ошибка сервера.']}), 500


@chat_bp.route('/dialogs/user', methods=['POST'])
def create_user_dialog_api():
    """
    Создать диалог от авторизованного пользователя (user).
    Требует JWT-аутентификации.
    Запрещено для: suser, admin.
    """
    user = g.current_user

    if user.role in ('suser', 'admin'):
        return jsonify({'success': False, 'errors': ['Администраторы и суперпользователи не могут создавать диалоги через этот интерфейс.']}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'errors': ['Ожидается JSON.']}), 400

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

    # Определение темы
    topic_id = None
    if context == 'product_question':
        topic_id = 1
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

    try:
        dialog = create_user_dialog(
            user_id=user.id,
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
        chat_logger.error(f"Ошибка валидации при создании диалога пользователем {user.id}: {e}")
        return jsonify({'success': False, 'errors': [str(e)]}), 400

    except Exception as e:
        db.session.rollback()
        chat_logger.exception(f"Неожиданная ошибка при создании диалога пользователем {user.id}")
        return jsonify({'success': False, 'errors': ['Внутренняя ошибка сервера.']}), 500


@chat_bp.route('/user-dialogs/<int:dialog_id>/messages', methods=['GET'])
def get_user_dialog_messages(dialog_id):
    """
    Возвращает сообщения диалога ТОЛЬКО если он принадлежит текущему пользователю.
    """
    user = g.current_user
    
    if user.role != 'user':
        return jsonify({'error': 'Доступ запрещён'}), 403

    dialog = Dialog.query.filter_by(id=dialog_id, user_id=user.id).first()
    if not dialog:
        return jsonify({'error': 'Диалог не найден или недоступен'}), 404

    try:
        unread_support_messages = Message.query.filter(
            Message.dialog_id == dialog_id,
            Message.sender_role.in_(['suser', 'admin']),
            Message.is_read == False
        ).all()

        for msg in unread_support_messages:
            msg.is_read = True

        db.session.commit()

        messages = Message.query.filter_by(dialog_id=dialog_id).order_by(Message.created_at.asc()).all()
        return jsonify([{
            'id': msg.id,
            'sender_role': msg.sender_role,
            'text': msg.text,
            'created_at': msg.created_at.isoformat()
        } for msg in messages]), 200

    except Exception as e:
        chat_logger.exception(f"Ошибка загрузки сообщений диалога {dialog_id}")
        return jsonify({'error': 'Ошибка сервера'}), 500


@chat_bp.route('/dialogs/<int:dialog_id>/messages', methods=['GET'])
def get_dialog_messages(dialog_id):
    """
    Возвращает все сообщения в указанном диалоге.
    
    Доступ: только для авторизованных suser/admin.
    При открытии диалога автоматически помечает сообщения от пользователя как прочитанные.
    """
    user = g.current_user
    if user.role not in ('suser', 'admin'):
        chat_logger.warning(
            f"Попытка доступа к диалогу {dialog_id} от недопустимой роли: {user.role} (user_id={user.id})"
        )
        return jsonify({'error': 'Доступ запрещён'}), 403

    try:
        dialog = db.session.get(Dialog, dialog_id)
        if not dialog:
            return jsonify({'error': 'Диалог не найден'}), 404

        unread_user_messages = Message.query.filter(
            Message.dialog_id == dialog_id,
            Message.sender_role.in_(['user', 'guest']),
            Message.is_read == False
        ).all()

        for msg in unread_user_messages:
            msg.is_read = True

        db.session.commit()

        messages = Message.query.filter_by(
            dialog_id=dialog_id
        ).order_by(
            Message.created_at.asc()
        ).all()

        return jsonify([{
            'id': msg.id,
            'sender_role': msg.sender_role,
            'text': msg.text,
            'created_at': msg.created_at.isoformat(),
            'is_read': msg.is_read
        } for msg in messages]), 200

    except Exception as e:
        db.session.rollback()
        chat_logger.exception(f"Ошибка при загрузке сообщений диалога {dialog_id}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@chat_bp.route('/user-dialogs/<int:dialog_id>/reply', methods=['POST'])
def send_user_reply(dialog_id):
    """Отправка сообщения от пользователя в свой диалог."""
    user = g.current_user
    if user.role != 'user':
        return jsonify({'error': 'Доступ запрещён'}), 403

    dialog = Dialog.query.filter_by(id=dialog_id, user_id=user.id).first()
    if not dialog:
        return jsonify({'error': 'Диалог не найден'}), 404

    if dialog.status != 'open':
        return jsonify({'error': 'Нельзя отвечать в закрытый диалог'}), 400

    data = request.get_json()
    text = data.get('text', '').strip() if data else ''
    if not text:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400

    try:
        message = send_message_in_dialog(
            dialog_id=dialog_id,
            sender_user_id=user.id,
            sender_role='user',
            text=text
        )
        return jsonify({
            'success': True,
            'message_id': message.id,
            'sent_at': message.created_at.isoformat()
        }), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        chat_logger.exception("Ошибка при отправке сообщения пользователем")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


from datetime import datetime

@chat_bp.route('/dialogs', methods=['GET'])
def get_all_dialogs():
    """
    Универсальный роут для получения списка диалогов.
    Сортировка: сначала непрочитанные, затем прочитанные, по дате обновления (новые выше).
    """
    user = g.current_user

    if user.role == 'user':
        dialogs = Dialog.query.filter(
            Dialog.user_id == user.id,
            Dialog.status == 'open'
        ).all()
    elif user.role == 'suser':
        dialogs = Dialog.query.filter(Dialog.topic_id == 1).all()
    elif user.role == 'admin':
        dialogs = Dialog.query.all()
    else:
        return jsonify({'error': 'Доступ запрещён'}), 403

    if user.role == 'user':
        incoming_sender_roles = ['suser', 'admin']
    else:
        incoming_sender_roles = ['user', 'guest']

    # Сначала подготовим данные с объектами datetime для сортировки
    dialog_data = []
    for dialog in dialogs:
        messages = Message.query.filter_by(dialog_id=dialog.id).all()
        message_count = len(messages)
        
        last_message = messages[0] if messages else None
        last_sender_role = last_message.sender_role if last_message else None
        
        last_message_preview = ''
        if last_message and last_message.text:
            preview = last_message.text.strip()
            last_message_preview = (preview[:100] + '…') if len(preview) > 100 else preview

        unread_count = sum(
            1 for msg in messages
            if msg.sender_role in incoming_sender_roles and not msg.is_read
        )

        # Сохраняем RAW данные, включая datetime объект
        dialog_data.append({
            'dialog': dialog,
            'messages': messages,
            'message_count': message_count,
            'last_message': last_message,
            'last_sender_role': last_sender_role,
            'last_message_preview': last_message_preview,
            'unread_count': unread_count
        })

    # === СОРТИРУЕМ ПО RAW ДАННЫМ ===
    dialog_data.sort(key=lambda item: (
        0 if item['unread_count'] > 0 else 1,  # непрочитанные вверх
        - (item['dialog'].updated_at.timestamp() if item['dialog'].updated_at else 0)  # новые выше
    ))

    # === Теперь формируем JSON-ответ ===
    result = []
    for item in dialog_data:
        dialog = item['dialog']
        result.append({
            'id': dialog.id,
            'user_id': dialog.user_id,
            'name': dialog.name,
            'email': dialog.email,
            'username': dialog.user.username if dialog.user else None,
            'topic_name': dialog.topic.name if dialog.topic else '—',
            'order_id': dialog.order_id,
            'product_id': dialog.product_id,
            'status': dialog.status,
            'updated_at': dialog.updated_at.isoformat() if dialog.updated_at else None,
            'message_count': item['message_count'],
            'last_sender_role': item['last_sender_role'],
            'last_message_preview': item['last_message_preview'],
            'unread_count': item['unread_count']
        })

    return jsonify(result), 200


@chat_bp.route('/dialogs/<int:dialog_id>/reply', methods=['POST'])
def send_reply_to_dialog(dialog_id):
    """
    Отправляет ответ от менеджера или администратора в существующий диалог.
    """
    user = g.current_user
    if user.role not in ('suser', 'admin'):
        chat_logger.warning(
            f"Попытка отправить ответ в диалог {dialog_id} от недопустимой роли: {user.role} (user_id={user.id})"
        )
        return jsonify({'error': 'Доступ запрещён'}), 403

    dialog = db.session.get(Dialog, dialog_id)
    if not dialog:
        return jsonify({'error': 'Диалог не найден'}), 404

    if dialog.status != 'open':
        return jsonify({'error': 'Нельзя отвечать в закрытый диалог'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Ожидается JSON'}), 400

    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400
    
    try:
        new_message = Message(
            dialog_id=dialog_id,
            sender_user_id=user.id,
            sender_role=user.role,
            text=text
        )

        db.session.add(new_message)
        dialog.updated_at = func.now()
        db.session.commit()

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

        return jsonify({
            'success': True,
            'message_id': new_message.id,
            'sent_at': new_message.created_at.isoformat()
        }), 201

    except Exception as e:
        db.session.rollback()
        chat_logger.exception(f"Критическая ошибка при отправке ответа в диалог {dialog_id}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500
    

@chat_bp.route('/dialogs/<int:dialog_id>/close', methods=['POST'])
def close_dialog(dialog_id):
    """
    Закрывает диалог, устанавливая статус в 'closed'.
    """
    user = g.current_user

    try:
        dialog = db.session.get(Dialog, dialog_id)
        if not dialog:
            return jsonify({'error': 'Диалог не найден'}), 404

        if user.role == 'user':
            if dialog.user_id != user.id:
                return jsonify({'error': 'Диалог недоступен'}), 403
        elif user.role not in ('suser', 'admin'):
            return jsonify({'error': 'Доступ запрещён'}), 403

        if dialog.status == 'closed':
            return jsonify({'success': True, 'message': 'Диалог уже закрыт'}), 200

        dialog.status = 'closed'
        db.session.commit()

        return jsonify({'success': True}), 200

    except Exception as e:
        db.session.rollback()
        chat_logger.exception(f"Ошибка при закрытии диалога {dialog_id}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@chat_bp.route('/dialogs/bulk-update-status', methods=['POST'])
def bulk_update_dialog_status():
    """
    Массовое обновление статуса для списка диалогов.
    """
    user = g.current_user

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Ожидается JSON'}), 400

    dialog_ids = data.get('dialog_ids')
    new_status = data.get('status')

    allowed_statuses = {'open', 'closed', 'archived'}
    if not isinstance(dialog_ids, list) or not dialog_ids:
        return jsonify({'error': 'Некорректный список диалогов'}), 400
    if new_status not in allowed_statuses:
        return jsonify({'error': 'Недопустимый статус'}), 400

    try:
        dialog_ids = list(set(int(did) for did in dialog_ids))

        dialogs = Dialog.query.filter(Dialog.id.in_(dialog_ids)).all()
        if len(dialogs) != len(dialog_ids):
            return jsonify({'error': 'Один или несколько диалогов не найдены'}), 404

        if user.role == 'user':
            for dialog in dialogs:
                if dialog.user_id != user.id:
                    return jsonify({'error': 'Диалог недоступен'}), 403
            if new_status == 'open':
                return jsonify({'error': 'Недостаточно прав для открытия диалога'}), 403

        elif user.role not in ('suser', 'admin'):
            return jsonify({'error': 'Доступ запрещён'}), 403

        for dialog in dialogs:
            dialog.status = new_status

        db.session.commit()
        return jsonify({'success': True, 'updated': len(dialogs)}), 200

    except ValueError:
        return jsonify({'error': 'Некорректный ID диалога'}), 400
    except Exception as e:
        db.session.rollback()
        chat_logger.exception("Ошибка массового обновления статуса диалогов")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


@chat_bp.route('/dialogs/bulk-delete', methods=['DELETE'])
def bulk_delete_dialogs():
    """
    Массовое удаление диалогов.
    """
    user = g.current_user

    if user.role == 'user':
        chat_logger.warning(f"Попытка удаления диалогов от user (ID={user.id})")
        return jsonify({'error': 'У вас нет прав на удаление диалогов'}), 403

    if user.role not in ('suser', 'admin'):
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    if not data or 'dialog_ids' not in data:
        return jsonify({'error': 'Ожидается JSON с dialog_ids'}), 400

    dialog_ids = data.get('dialog_ids')
    if not isinstance(dialog_ids, list) or not dialog_ids:
        return jsonify({'error': 'Некорректный список диалогов'}), 400

    try:
        dialog_ids = [int(did) for did in dialog_ids]
        if len(dialog_ids) != len(set(dialog_ids)):
            return jsonify({'error': 'Обнаружены дубликаты ID'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'Некорректный ID диалога'}), 400

    try:
        dialogs = Dialog.query.filter(Dialog.id.in_(dialog_ids)).options(
            db.joinedload(Dialog.topic)
        ).all()

        if len(dialogs) != len(dialog_ids):
            return jsonify({'error': 'Один или несколько диалогов не найдены'}), 404

        for dialog in dialogs:
            if user.role == 'suser':
                if dialog.topic_id != 1:
                    chat_logger.warning(
                        f"suser (ID={user.id}) пытался удалить диалог {dialog.id} "
                        f"с topic_id={dialog.topic_id}"
                    )
                    return jsonify({
                        'error': 'Вы можете удалять только диалоги по теме "Вопрос о товаре" (topic_id=1)'
                    }), 403

        for dialog in dialogs:
            db.session.delete(dialog)

        db.session.commit()
        return jsonify({'success': True, 'deleted': len(dialogs)}), 200

    except Exception as e:
        db.session.rollback()
        chat_logger.exception("Ошибка массового удаления диалогов")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500