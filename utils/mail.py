# Модуль отвечает за отправку служебных писем по электронной почте и валидацию введённого email.
from flask_mail import Message
from extensions import mail
from smtplib import SMTPException
from email_validator import validate_email, EmailNotValidError
import logging

chat_logger = logging.getLogger('app.chat')


def send_password_reset_email(user, reset_url):  # Отправляет пользователю ссылку для сброса пароля,
    subject = "Сброс пароля"
    body = f"""Для сброса пароля перейдите по ссылке:
            {reset_url}
            Если вы не запрашивали сброс пароля — проигнорируйте это сообщение."""

    try:
        msg = Message(subject, recipients=[user.email], body=body)
        mail.send(msg)
        return True
    except SMTPException as e:
        print(f"[Ошибка отправки email] {e}")
        return False

def send_confirm_email(email, confirm_url):  # Отправляет ссылку для подтверждения email-адреса.
    subject = "Подтверждение email"
    body = f"""Для подтверждения email перейдите по ссылке:
    {confirm_url}
    Если вы нигде не регистрировались, пожалуйста, проигнорируйте это сообщение."""
    
    try:
        msg = Message(subject, recipients=[email], body=body)
        mail.send(msg)
        return True
    except SMTPException as e:
        print(f"[Ошибка отправки email] {e}")
        return False

def send_guest_dialog_reply(
    dialog_id: int,
    guest_name: str,
    guest_email: str,
    reply_text: str,
    sender_role: str
) -> bool:
    """
    Отправляет гостю ответ на его вопрос в диалоге.
    
    Args:
        dialog_id (int): ID диалога
        guest_name (str): Имя гостя
        guest_email (str): Email гостя
        reply_text (str): Текст ответа
        sender_role (str): Роль отправителя — 'suser' или 'admin'

    Returns:
        bool: True при успехе, False при ошибке
    """
    # Определяем отображаемое имя по роли
    role_labels = {
        'suser': 'Менеджер',
        'admin': 'Администратор'
    }
    sender_display_name = role_labels.get(sender_role, 'Специалист поддержки')

    subject = "Ответ на ваш вопрос"
    body = f"""Здравствуйте, {guest_name}!

    Вам ответил {sender_display_name} (диалог #{dialog_id}):

    {reply_text}

    С уважением,
    Команда поддержки MaMoto
    """

    try:
        msg = Message(subject=subject, recipients=[guest_email], body=body)
        mail.send(msg)
        return True
    except SMTPException as e:
        chat_logger.error(f"[Ошибка отправки email гостю] {e}")
        return False


def normalize_email(email: str) -> str | None:
    """
    Валидирует и нормализует email-адрес.
    
    Возвращает:
        str — нормализованный email (например, 'user@gmail.com'), если адрес валиден.
        None — если email пустой, не строка, или не прошёл валидацию.
    """
    if not email or not isinstance(email, str):
        return None
    try:
        valid = validate_email(email.strip())
        return valid.email  # в нижнем регистре и без лишних символов
    except EmailNotValidError:
        return None