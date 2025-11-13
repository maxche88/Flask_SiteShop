# Модуль для избежания циклический импортов.
import logging
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()

sys_logger = logging.getLogger('app.system')


# Декоратор из flask-jwt-extended, который регистрирует функцию, вызываемую каждый раз, когда поступает запрос с JWT-токеном.
@jwt.token_in_blocklist_loader
def check_if_token_revoked(_, jwt_payload):
    jti = jwt_payload.get("jti")
    user_id = jwt_payload.get("sub", "unknown")

    from models import UserToken
    token = UserToken.query.filter_by(jti=jti).first()

    is_revoked = token is not None and token.revoked

    if is_revoked:
        sys_logger.warning(f"Обнаружена попытка использования ОТЗВАННОГО токена! user_id={user_id}, jti={jti}")

    return is_revoked