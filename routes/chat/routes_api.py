from flask import Blueprint, request, jsonify
from extensions import db
from models import Dialog, Message, User, MessageTopic
from services.chat_service import create_guest_dialog, create_user_dialog, send_message_in_dialog
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


@chat_bp.route('/unread-count', methods=['GET'])
def get_unread_message_count():
    """
    Возвращает количество непрочитанных сообщений для ТЕКУЩЕГО пользователя.
    
    - Для авторизованного 'user': непрочитанные сообщения от поддержки.
    - Для авторизованного 'suser'/'admin': непрочитанные сообщения от пользователей.
    - Для гостей: возвращает 0 (гости не имеют аккаунта и не получают сообщений в системе).
    
    """
    user_id_str = get_safe_user_id()
    
    # Гости не имеют непрочитанных сообщений в системе
    if not user_id_str:
        return jsonify({'unread_count': 0}), 200

    try:
        user_id = int(user_id_str)
        user = User.query.get(user_id)
        if not user:
            return jsonify({'unread_count': 0}), 200
    except (TypeError, ValueError):
        return jsonify({'unread_count': 0}), 200

    try:
        if user.role == 'user':
            # Только его диалоги, сообщения от поддержки
            count = db.session.query(Message).join(Dialog).filter(
                Dialog.user_id == user.id,
                Message.sender_role.in_(['suser', 'admin']),
                Message.is_read == False
            ).count()

        elif user.role in ('suser', 'admin'):
            # Все сообщения от пользователей (в любых диалогах)
            count = db.session.query(Message).filter(
                Message.sender_role.in_(['user', 'guest']),
                Message.is_read == False
            ).count()

        else:
            count = 0

        return jsonify({'unread_count': count}), 200

    except Exception as e:
        chat_logger.exception("Ошибка при подсчёте непрочитанных сообщений")
        return jsonify({'unread_count': 0}), 200  # не ломаем фронтенд


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


@chat_bp.route('/user-dialogs/<int:dialog_id>/messages', methods=['GET'])
def get_user_dialog_messages(dialog_id):
    """
    Возвращает сообщения диалога ТОЛЬКО если он принадлежит текущему пользователю.
    """
    current_user_id = get_safe_user_id()
    if not current_user_id:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'Некорректный ID'}), 400

    user = User.query.get(user_id)
    if not user or user.role != 'user':
        return jsonify({'error': 'Доступ запрещён'}), 403

    dialog = Dialog.query.filter_by(id=dialog_id, user_id=user_id).first()
    if not dialog:
        return jsonify({'error': 'Диалог не найден или недоступен'}), 404

    try:
         # Помечаем сообщения от поддержки как прочитанные
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
        chat_logger.warning(
            f"Попытка доступа к диалогу {dialog_id} от недопустимой роли: "
            f"{user.role if user else 'None'} (user_id={current_user_id})"
        )
        return jsonify({'error': 'Доступ запрещён'}), 403

    try:
        # Проверяем существование диалога
        dialog = Dialog.query.get(dialog_id)
        if not dialog:
            return jsonify({'error': 'Диалог не найден'}), 404

        # Помечаем сообщения ОТ ПОЛЬЗОВАТЕЛЯ как прочитанные
        unread_user_messages = Message.query.filter(
            Message.dialog_id == dialog_id,
            Message.sender_role.in_(['user', 'guest']),
            Message.is_read == False
        ).all()

        for msg in unread_user_messages:
            msg.is_read = True

        db.session.commit()

        # Загружаем все сообщения
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
    current_user_id = get_safe_user_id()
    if not current_user_id:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'Некорректный ID'}), 400

    user = User.query.get(user_id)
    if not user or user.role != 'user':
        return jsonify({'error': 'Доступ запрещён'}), 403

    dialog = Dialog.query.filter_by(id=dialog_id, user_id=user_id).first()
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
            sender_user_id=user_id,
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


# SUSER/ADMIN/USER
@chat_bp.route('/dialogs', methods=['GET'])
def get_all_dialogs():
    """
    Универсальный роут для получения списка диалогов.
    
    Поведение зависит от роли текущего пользователя:
    
      - 'user': видит только СВОИ ОТКРЫТЫЕ диалоги.
      - 'suser': видит ВСЕ диалоги с topic_id = 1.
      - 'admin': видит ВСЕ диалоги.
    
    Для всех:
      - unread_count = непрочитанные от клиентов (user/guest) — для поддержки,
      - unread_count = непрочитанные от поддержки (suser/admin) — для пользователя.
    
    Гости не могут вызвать этот роут (требуется авторизация).
    """
    current_user_id = get_safe_user_id()
    if not current_user_id:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'Некорректный идентификатор пользователя'}), 400

    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    # === 1. Фильтрация диалогов по роли ===
    if user.role == 'user':
        # Пользователь: только свои ОТКРЫТЫЕ диалоги
        dialogs = Dialog.query.filter(
            Dialog.user_id == user.id,
            Dialog.status == 'open'
        ).order_by(Dialog.updated_at.desc()).all()

    elif user.role == 'suser':
        # Менеджер: только диалоги с topic_id = 1
        dialogs = Dialog.query.filter(
            Dialog.topic_id == 1
        ).order_by(Dialog.updated_at.desc()).all()

    elif user.role == 'admin':
        # Админ: все диалоги
        dialogs = Dialog.query.order_by(Dialog.updated_at.desc()).all()

    else:
        return jsonify({'error': 'Доступ запрещён'}), 403

    # === 2. Определяем, чьи сообщения считать "входящими" ===
    if user.role == 'user':
        incoming_sender_roles = ['suser', 'admin']
    else:
        # Для suser и admin — входящие от клиентов
        incoming_sender_roles = ['user', 'guest']

    # === 3. Формируем результат ===
    result = []
    for dialog in dialogs:
        messages = Message.query.filter_by(dialog_id=dialog.id).order_by(Message.created_at.desc()).all()
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
            'message_count': message_count,
            'last_sender_role': last_sender_role,
            'last_message_preview': last_message_preview,
            'unread_count': unread_count
        })

    return jsonify(result), 200


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
    

@chat_bp.route('/dialogs/<int:dialog_id>/close', methods=['POST'])
def close_dialog(dialog_id):
    """
    Закрывает диалог, устанавливая статус в 'closed'.
    
    Доступ:
      - Авторизованный 'user' — может закрыть СВОЙ диалог.
      - 'suser'/'admin' — могут закрыть ЛЮБОЙ диалог.
    
    Args:
        dialog_id (int): ID диалога
    
    Returns:
        JSON: { "success": true } или ошибка
    """
    current_user_id = get_safe_user_id()
    if not current_user_id:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'Некорректный идентификатор пользователя'}), 400

    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    try:
        dialog = Dialog.query.get(dialog_id)
        if not dialog:
            return jsonify({'error': 'Диалог не найден'}), 404

        # Проверка прав доступа
        if user.role == 'user':
            # Пользователь может закрыть только свой диалог
            if dialog.user_id != user.id:
                return jsonify({'error': 'Диалог недоступен'}), 403
        elif user.role not in ('suser', 'admin'):
            return jsonify({'error': 'Доступ запрещён'}), 403

        # Уже закрыт?
        if dialog.status == 'closed':
            return jsonify({'success': True, 'message': 'Диалог уже закрыт'}), 200

        # Закрываем
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
    
    Доступ:
      - 'user': может обновлять ТОЛЬКО свои диалоги, и только на 'closed' или 'archived'
      - 'suser'/'admin': могут обновлять ЛЮБЫЕ диалоги на любой статус.
    
    JSON:
    {
        "dialog_ids": [1, 2, 3],
        "status": "closed"  // open | closed | archived
    }
    """
    current_user_id = get_safe_user_id()
    if not current_user_id:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'Некорректный ID пользователя'}), 400

    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

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
        # Преобразуем ID в int и убираем дубли
        dialog_ids = list(set(int(did) for did in dialog_ids))

        # Загружаем диалоги
        dialogs = Dialog.query.filter(Dialog.id.in_(dialog_ids)).all()
        if len(dialogs) != len(dialog_ids):
            return jsonify({'error': 'Один или несколько диалогов не найдены'}), 404

        # Проверка прав
        if user.role == 'user':
            # Пользователь может менять только свои диалоги
            for dialog in dialogs:
                if dialog.user_id != user.id:
                    return jsonify({'error': 'Диалог недоступен'}), 403
            # И не может открывать диалогы
            if new_status == 'open':
                return jsonify({'error': 'Недостаточно прав для открытия диалога'}), 403

        elif user.role not in ('suser', 'admin'):
            return jsonify({'error': 'Доступ запрещён'}), 403

        # Обновляем статус
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
    
    Права доступа:
      - 'user': запрещено полностью.
      - 'suser': может удалять ТОЛЬКО диалоги с topic_id = 1.
      - 'admin': может удалять ЛЮБЫЕ диалоги.
    
    JSON:
    {
        "dialog_ids": [1, 2, 3]
    }
    """
    current_user_id = get_safe_user_id()
    if not current_user_id:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        current_user_id = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'Некорректный ID пользователя'}), 400

    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    # Запрет для user
    if user.role == 'user':
        chat_logger.warning(f"Попытка удаления диалогов от user (ID={user.id})")
        return jsonify({'error': 'У вас нет прав на удаление диалогов'}), 403

    # Только suser и admin могут продолжить
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
        # Загружаем диалоги со связанными темами
        dialogs = Dialog.query.filter(Dialog.id.in_(dialog_ids)).options(
            db.joinedload(Dialog.topic)
        ).all()

        if len(dialogs) != len(dialog_ids):
            return jsonify({'error': 'Один или несколько диалогов не найдены'}), 404

        # Проверка прав в зависимости от роли
        for dialog in dialogs:
            if user.role == 'suser':
                # suser может удалять только topic_id = 1
                if dialog.topic_id != 1:
                    chat_logger.warning(
                        f"suser (ID={user.id}) пытался удалить диалог {dialog.id} "
                        f"с topic_id={dialog.topic_id}"
                    )
                    return jsonify({
                        'error': 'Вы можете удалять только диалоги по теме "Вопрос о товаре" (topic_id=1)'
                    }), 403

            # Для admin — никаких ограничений

        # Удаляем все диалоги
        for dialog in dialogs:
            db.session.delete(dialog)

        db.session.commit()
        return jsonify({'success': True, 'deleted': len(dialogs)}), 200

    except Exception as e:
        db.session.rollback()
        chat_logger.exception("Ошибка массового удаления диалогов")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500