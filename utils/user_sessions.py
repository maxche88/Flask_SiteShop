import logging
from flask import current_app
from flask_jwt_extended import (
    create_access_token,
    get_jti,
    verify_jwt_in_request,
    get_jwt_identity
)
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt import (
    ExpiredSignatureError,
    DecodeError
)
from datetime import datetime, timezone, timedelta
from models import UserToken, User
from extensions import db


sys_logger = logging.getLogger('app.system')

def create_access_token_for_user(user_id):
    """
    Создаёт JWT access-токен для пользователя и сохраняет его в базу данных
    как активную сессию (revoked=False).
    
    :param user_id: ID пользователя
    :return: str — JWT access token
    """
    # Генерация токена
    access_token = create_access_token(identity=str(user_id))

    # Извлечение JTI
    jti = get_jti(encoded_token=access_token)

    # Определение срока действия
    expires_delta = current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', timedelta(minutes=15))
    # Если в конфиге время не задано — используется значение по умолчанию: 15 минут
    if isinstance(expires_delta, int):
        expires_delta = timedelta(seconds=expires_delta)

    issued_at = datetime.now(timezone.utc)  # Текущее время в формате UTC.
    expires_at = issued_at + expires_delta  # Время, когда токен перестанет быть валидным.

    # Сохранение в БД
    token_record = UserToken(
        jti=jti,
        user_id=user_id,
        issued_at=issued_at,
        expires_at=expires_at,
        revoked=False
    )

    db.session.add(token_record)

    return access_token

def get_safe_user_id():
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()

        if user_id is None:
            sys_logger.debug("JWT присутствует, но не содержит user_id (identity is None)")
            return None

        if User.query.get(user_id):
            return str(user_id)
        else:
            sys_logger.warning(f"JWT содержит user_id={user_id}, но пользователь не найден в БД")
            return None

    except ExpiredSignatureError:
        sys_logger.debug("JWT просрочен — трактуем как отсутствие аутентификации")
        return None

    except JWTExtendedException as e:
        error_msg = str(e).lower()
        if "revoked" in error_msg:
            sys_logger.debug("Получен отозванный JWT — трактуем как отсутствие аутентификации")
        else:
            sys_logger.debug(f"JWT недействителен: {e}")
        return None

    except DecodeError as e:
        sys_logger.debug(f"JWT не может быть обработан: {type(e).__name__}: {e}")
        return None

    except Exception as e:
        sys_logger.error(f"Неожиданная ошибка в get_safe_user_id: {e}", exc_info=True)
        return None