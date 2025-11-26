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


auth_logger = logging.getLogger('app.auth')
sys_logger = logging.getLogger('app.system')


def create_access_token_for_user(user_id):
    """
    Создаёт JWT access-токен для пользователя и сохраняет его в базу данных
    как активную сессию (revoked=False).
    
    :param user_id: ID пользователя
    :return: str — JWT access token
    """
    # Генерация токена
    # Передаём user_id как строку, потому что flask-jwt-extended в режиме работы с cookie
    # (при JWT_TOKEN_LOCATION = ['cookies']) требует, чтобы значение identity было строкой.
    # Несмотря на то, что PyJWT >= 2.0 формально поддерживает int в поле "sub",
    # внутренняя логика flask-jwt-extended при генерации токена для cookie
    # может вызывать ошибку "Subject must be a string", если identity не str.
    # Это известное ограничение, связанное с совместимостью и сериализацией метаданных.
    # В остальном коде (включая БД и бизнес-логику) user_id используется как int.
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
    """
    Предназначена для безопасного извлечения идентификатора пользователя из JWT при наличии валидного токена.
    """
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()

        if user_id is None:
            auth_logger.debug("JWT присутствует, но не содержит user_id (identity is None)")
            return None

        if User.query.get(user_id):
            return user_id
        else:
            auth_logger.warning(f"JWT содержит user_id={user_id}, но пользователь не найден в БД")
            return None

    except (ExpiredSignatureError, DecodeError, JWTExtendedException) as e:
        # Все JWT-специфичные ошибки: просрочен, подделан, отозван, не раскодирован и т.д.
        # Отозванные токены уже залогированы в @jwt.token_in_blocklist_loader,
        # поэтому здесь логируем всё единообразно без специальной обработки "revoked".
        error_type = type(e).__name__
        auth_logger.debug(f"JWT недействителен: {error_type}: {e}")
        return None

    except Exception as e:
        # Любые другие неожиданные ошибки (например, проблемы с БД)
        sys_logger.error(f"Неожиданная ошибка в get_safe_user_id: {type(e).__name__}: {e}", exc_info=True)
        return None