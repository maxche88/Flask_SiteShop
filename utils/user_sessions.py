import logging
from flask import current_app
from flask_jwt_extended import create_access_token, get_jti, verify_jwt_in_request, get_jwt_identity
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


# def revoke_all_user_tokens(user_id):
#     """
#     Отзывает все токены пользователя (устанавливает revoked=True).
#     """
#     UserToken.query.filter_by(user_id=user_id).update({'revoked': True})


# def has_active_token(user_id):
#     """
#     Проверяет, существует ли у пользователя хотя бы один активный (не отозванный и не истёкший) токен.
    
#     :return: bool
#     """
#     now = datetime.utcnow()
#     return db.session.query(UserToken.id).filter(
#         UserToken.user_id == user_id,
#         UserToken.revoked.is_(False),
#         UserToken.expires_at > now
#     ).first() is not None


def get_safe_user_id():
    """
    Возвращает user_id (str), если токен валиден.
    Возвращает None во всех остальных случаях (просрочен, отозван, отсутствует).
    """
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id is not None:
            # Проверяем, существует ли пользователь
            if User.query.get(user_id):
                return str(user_id)
            else:
                sys_logger.warning(f"JWT содержит user_id={user_id}, но пользователь не найден в БД")
        else:
            sys_logger.debug("JWT не содержит user_id (identity is None)")
    except Exception as e:
        sys_logger.error(f"Ошибка в get_safe_user_id: {e}", exc_info=True)
    
    return None