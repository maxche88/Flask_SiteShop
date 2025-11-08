from datetime import timedelta
from flask import current_app
from utils.time import current_time
from models import db, User, IPAttemptLog


def get_unconfirmed_cutoff():
    """
    Возвращает naive datetime, соответствующий моменту "сейчас - TTL из конфига".
    Используется для сравнения с User.created_at (который naive).
    """
    ttl_minutes = current_app.config['UNCONFIRMED_USER_TTL_MINUTES']
    aware_cutoff = current_time() - timedelta(minutes=ttl_minutes)
    return aware_cutoff.replace(tzinfo=None)


def get_unconfirmed_users_older_than_ttl():
    """
    Возвращает список неподтверждённых пользователей, чья дата создания
    старше допустимого срока из конфигурации (UNCONFIRMED_USER_TTL_MINUTES).
    """
    cutoff = get_unconfirmed_cutoff()
    return User.query.filter(
        User.confirm_email.is_(False),
        User.created_at.isnot(None),
        User.created_at < cutoff
    ).all()


def delete_unconfirmed_users_older_than_ttl():
    """
    Удаляет неподтверждённых пользователей, зарегистрировавшихся
    ранее допустимого срока из конфигурации (UNCONFIRMED_USER_TTL_MINUTES).
    Также удаляет связанные записи в IPAttemptLog.
    """
    cutoff = get_unconfirmed_cutoff()

    # Сначала получаем ID пользователей для безопасного удаления связанных данных
    users_to_delete = User.query.filter(
        User.confirm_email.is_(False),
        User.created_at.isnot(None),
        User.created_at < cutoff
    ).all()

    deleted_count = 0
    for user in users_to_delete:
        IPAttemptLog.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        deleted_count += 1

    db.session.commit()
    return deleted_count