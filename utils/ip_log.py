from flask import request
from models import db, IPAttemptLog


def get_client_ip():
    """Получает реальный IP-адрес клиента с учётом прокси (X-Forwarded-For)."""
    if request.headers.getlist("X-Forwarded-For"):
        # X-Forwarded-For может содержать несколько IP, первый — исходный клиент
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    return request.remote_addr


def ensure_ip_log_entry(user=None):
    """
    Гарантирует наличие записи в IPAttemptLog для текущего IP.
    - Если запись с таким IP и без user_id существует — обновляет её (привязывает пользователя, сбрасывает счётчик).
    - Если записи нет — создаёт новую.
    - Если пользователь уже известен — создаёт/обновляет запись с привязкой к нему.
    
    Возвращает объект IPAttemptLog (либо существующий, либо новый).
    """
    client_ip = get_client_ip()
    if not client_ip:
        raise ValueError("Не удалось определить IP-адрес клиента")

    # Ищем запись по IP и (если передан пользователь) без user_id — чтобы обновить "висячую" запись
    ip_log = None
    if user:
        # Сначала попробуем найти запись без привязки — чтобы привязать к пользователю
        ip_log = IPAttemptLog.query.filter_by(ip_address=client_ip, user_id=None).first()
        if ip_log:
            ip_log.user_id = user.id
            ip_log.recovery_attempts_count = 3
            db.session.commit()
            return ip_log

    # Если не нашли "висячую" запись — ищем любую запись по IP
    ip_log = IPAttemptLog.query.filter_by(ip_address=client_ip).first()
    if ip_log:
        # Если запись есть, но без пользователя — можно привязать (на случай, если user передан позже)
        if user and ip_log.user_id is None:
            ip_log.user_id = user.id
            ip_log.recovery_attempts_count = 3
            db.session.commit()
        return ip_log

    # Если записи нет — создаём новую
    ip_log = IPAttemptLog(
        ip_address=client_ip,
        user_id=user.id if user else None,
        recovery_attempts_count=3
    )
    db.session.add(ip_log)
    db.session.commit()
    return ip_log


def reset_recovery_attempts_for_ip(user):
    """
    Сбрасывает счётчик попыток восстановления пароля для текущего IP.
    Привязывает IP к пользователю, если ещё не привязан.
    Используется при успешном входе или смене пароля.
    """
    client_ip = get_client_ip()
    if not client_ip:
        return

    # Находим все записи для этого IP и сбрасываем счётчик
    logs = IPAttemptLog.query.filter_by(ip_address=client_ip).all()
    updated = False
    for log in logs:
        log.recovery_attempts_count = 3
        if log.user_id is None:
            log.user_id = user.id
        updated = True

    if not logs:
        # На всякий случай создаём запись
        new_log = IPAttemptLog(ip_address=client_ip, user_id=user.id, recovery_attempts_count=3)
        db.session.add(new_log)
        updated = True

    if updated:
        db.session.commit()