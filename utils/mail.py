# Модуль отвечает за отправку служебных писем по электронной почте.

from flask_mail import Message
from extensions import mail
from smtplib import SMTPException

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