from datetime import timedelta
from flask import current_app
from utils.time import current_time
from models import db, User, IPAttemptLog

def delete_unconfirmed_users_older_than(hours=24):
    """
    Удаляет неподтверждённых пользователей, зарегистрировавшихся более `hours` часов назад.
    Использует единый источник времени — utils.time.current_time().
    """
    now = current_time()
    cutoff_time = now - timedelta(hours=hours)

    unconfirmed_users = User.query.filter(
        User.confirm_email.is_(False),
        User.created_at.isnot(None),
        User.created_at < cutoff_time
    ).all()

    deleted_count = 0
    for user in unconfirmed_users:
        IPAttemptLog.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        deleted_count += 1

    db.session.commit()
    return deleted_count

def get_unconfirmed_users_older_than(hours=24):
    """Возвращает список неподтверждённых пользователей старше N часов (без удаления)."""
    now = current_time()
    cutoff = now - timedelta(hours=hours)
    return User.query.filter(
        User.confirm_email.is_(False),
        User.created_at.isnot(None),
        User.created_at < cutoff
    ).all()

def get_unconfirmed_cutoff():
    """
    Возвращает naive datetime, соответствующий (сейчас - timedelta_obj).
    Используется для сравнения с User.created_at (который naive).
    """
    ttl_minutes = current_app.config['UNCONFIRMED_USER_TTL_MINUTES']
    from datetime import timedelta
    aware_cutoff = current_time() - timedelta(minutes=ttl_minutes)
    return aware_cutoff.replace(tzinfo=None)