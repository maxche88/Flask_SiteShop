# Модуль для избежания циклический импортов.

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from datetime import datetime, timezone


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()


# Колбэк для проверки отзыва токена
@jwt.token_in_blocklist_loader
def check_if_token_revoked(_, jwt_payload):
    jti = jwt_payload["jti"]
    from models import UserToken
    token = UserToken.query.filter_by(jti=jti).first()
    return token is not None and (token.revoked or datetime.now(timezone.utc) >= token.expires_at)