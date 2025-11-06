# Модуль отвечает за отправку служебных писем по электронной почте и валидацию введённого email.
from flask_mail import Message
from extensions import mail
from smtplib import SMTPException
from email_validator import validate_email, EmailNotValidError


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