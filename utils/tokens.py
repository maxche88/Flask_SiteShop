# Генерирует JWT-токены.
from flask import current_app
from flask_jwt_extended import create_access_token
from datetime import timedelta



def generate_password_reset_token(email):  # Создаёт токен для сброса пароля (действует 30 минут)
    expires = timedelta(minutes=30)
    return create_access_token(
        identity=email,
        expires_delta=expires,
        additional_claims={"type": "password_reset"}
    )

def generate_email_confirmation_token(email):
    ttl_minutes = current_app.config['UNCONFIRMED_USER_TTL_MINUTES']
    return create_access_token(
        identity=email,
        expires_delta=timedelta(minutes=ttl_minutes),
        additional_claims={'type': 'email_confirmation'}
    )