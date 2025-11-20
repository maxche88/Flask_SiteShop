"""
Слой бизнес-логики для работы с чатом.
Содержит функции создания диалогов, отправки сообщений, управления статусом.
Не зависит от Flask, JWT, HTTP или фронтенда.
"""

from models import Dialog, Message, MessageTopic, Shop, Order, User, db
from sqlalchemy.exc import IntegrityError


# Создание диалогов
def create_user_dialog(user_id, topic_id, text, product_id=None, order_id=None):
    """
    Создаёт диалог от авторизованного пользователя.

    Args:
        user_id (int): ID пользователя из таблицы users
        topic_id (int): ID темы из message_topics
        text (str): Текст первого сообщения (1–300 символов)
        product_id (int, optional): ID товара из shop
        order_id (int, optional): ID заказа из orders

    Returns:
        Dialog: созданный диалог

    Raises:
        ValueError: при недопустимых данных
        IntegrityError: при нарушении целостности БД
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError("Пользователь не найден")

    _validate_topic(topic_id)
    _validate_product_or_order(product_id, order_id)
    _validate_message_text(text)

    dialog = Dialog(
        user_id=user_id,
        name=user.username,
        email=user.email,
        topic_id=topic_id,
        product_id=product_id,
        order_id=order_id,
        status='open'
    )
    db.session.add(dialog)
    db.session.flush()

    message = Message(
        dialog_id=dialog.id,
        sender_user_id=user_id,
        sender_role='user',
        text=text
    )
    db.session.add(message)
    db.session.commit()

    return dialog


def create_guest_dialog(guest_name, guest_email, topic_id, text, product_id=None, order_id=None):
    """
    Создаёт диалог от гостя.

    Args:
        guest_name (str): Имя гостя (1–100 символов)
        guest_email (str): Email гостя
        topic_id (int): ID темы
        text (str): Текст сообщения (1–300 символов)
        product_id (int, optional)
        order_id (int, optional)

    Returns:
        Dialog

    Raises:
        ValueError, IntegrityError
    """
    if not guest_name or len(guest_name.strip()) == 0:
        raise ValueError("Имя не может быть пустым")
    if not guest_email or '@' not in guest_email:
        raise ValueError("Некорректный email")

    _validate_topic(topic_id)
    _validate_product_or_order(product_id, order_id)
    _validate_message_text(text)

    dialog = Dialog(
        user_id=None,
        name=guest_name.strip(),
        email=guest_email.strip(),
        topic_id=topic_id,
        product_id=product_id,
        order_id=order_id,
        status='open'
    )
    db.session.add(dialog)
    db.session.flush()

    message = Message(
        dialog_id=dialog.id,
        sender_role='guest',
        text=text
    )
    db.session.add(message)
    db.session.commit()

    return dialog


# Отправка сообщений в существующий диалог
def send_message_in_dialog(dialog_id, sender_user_id, sender_role, text):
    """
    Отправляет сообщение в существующий диалог.

    Args:
        dialog_id (int): ID диалога
        sender_user_id (int or None): ID отправителя (None для гостя, но гость не может писать после первого сообщения)
        sender_role (str): 'user', 'suser', 'admin' (гость не поддерживается здесь)
        text (str): Текст сообщения

    Returns:
        Message

    Raises:
        ValueError: если диалог закрыт или данные недействительны
    """
    _validate_message_text(text)

    dialog = Dialog.query.get(dialog_id)
    if not dialog:
        raise ValueError("Диалог не найден")
    if dialog.status != 'open':
        raise ValueError("Нельзя отправлять сообщения в закрытый диалог")

    # Для авторизованных — проверяем, что пользователь имеет доступ
    if sender_role in ('user', 'suser', 'admin'):
        if sender_role == 'user' and dialog.user_id != sender_user_id:
            raise ValueError("Вы не можете писать в этот диалог")

    message = Message(
        dialog_id=dialog_id,
        sender_user_id=sender_user_id,
        sender_role=sender_role,
        text=text
    )
    db.session.add(message)
    db.session.commit()

    # Обновляем updated_at у диалога
    dialog.updated_at = db.func.now()
    db.session.commit()

    return message


# Получение данных
def get_user_dialogs(user_id):
    """
    Возвращает все диалоги пользователя.

    Args:
        user_id (int)

    Returns:
        List[Dialog]
    """
    return Dialog.query.filter_by(user_id=user_id).order_by(Dialog.created_at.desc()).all()


def get_dialog_history(dialog_id):
    """
    Возвращает все сообщения в диалоге.

    Args:
        dialog_id (int)

    Returns:
        List[Message]
    """
    return Message.query.filter_by(dialog_id=dialog_id).order_by(Message.created_at).all()


def get_dialog_by_id(dialog_id):
    """Возвращает диалог по ID."""
    return Dialog.query.get(dialog_id)


# Управление статусом
def close_dialog(dialog_id, closed_by_user_id):
    """
    Закрывает диалог (только для suser/admin).

    Args:
        dialog_id (int)
        closed_by_user_id (int): ID менеджера или админа

    Returns:
        Dialog
    """
    user = User.query.get(closed_by_user_id)
    if not user or user.role not in ('suser', 'admin'):
        raise ValueError("Только менеджер или админ может закрывать диалоги")

    dialog = Dialog.query.get(dialog_id)
    if not dialog:
        raise ValueError("Диалог не найден")

    dialog.status = 'closed'
    db.session.commit()
    return dialog


# Вспомогательные функции валидации
def _validate_user(user_id):
    if not User.query.get(user_id):
        raise ValueError("Пользователь не найден")


def _validate_topic(topic_id):
    topic = MessageTopic.query.get(topic_id)
    if not topic or not topic.is_active:
        raise ValueError("Выбранная тема обращения недоступна")


def _validate_product_or_order(product_id, order_id):
    if product_id is not None and not Shop.query.get(product_id):
        raise ValueError("Указанный товар не найден")
    if order_id is not None and not Order.query.get(order_id):
        raise ValueError("Указанный заказ не найден")


def _validate_message_text(text):
    text = text.strip()
    if not text:
        raise ValueError("Сообщение не может быть пустым")
    if len(text) > 300:
        raise ValueError("Сообщение не должно превышать 300 символов")