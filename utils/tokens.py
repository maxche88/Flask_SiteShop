# Генерирует JWT-токены.
from flask import current_app
from flask_jwt_extended import create_access_token
from datetime import timedelta



def generate_password_reset_token(email):
    """
    Создаёт временный JWT-токен (30 минут) для сброса пароля с типом password_reset.
    Идентификатор — email пользователя. 
    """
    ttl_minutes = current_app.config.get('PASSWORD_RESET_TOKEN_TTL_MINUTES', 30)
    return create_access_token(
        identity=email,
        expires_delta=timedelta(minutes=ttl_minutes),
        additional_claims={"type": "password_reset"}
    )

def generate_email_confirmation_token(email):
    """
    Создаёт временный JWT-токен для подтверждения email.
    Срок действия берётся из настроек (UNCONFIRMED_USER_TTL_MINUTES). Тип — email_confirmation. 
    """
    ttl_minutes = current_app.config.get('UNCONFIRMED_USER_TTL_MINUTES', 1440)
    return create_access_token(
        identity=email,
        expires_delta=timedelta(minutes=ttl_minutes),
        additional_claims={'type': 'email_confirmation'}
    )

