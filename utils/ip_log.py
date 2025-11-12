from flask import request
from models import db, IPAttemptLog


def get_client_ip():
    """Возвращает реальный IP-адрес клиента."""
    return request.remote_addr


def get_or_create_ip_log(client_ip: str) -> IPAttemptLog:
    """
    Получает запись IPAttemptLog по IP-адресу.
    Если записи нет — создаёт новую с recovery_attempts_count = 3.
    
    Функция гарантирует, что для любого переданного IP-адреса всегда 
    будет возвращён соответствующий объект IPAttemptLog — либо существующий, 
    либо новый с начальным счётчиком попыток восстановления, равным 3.
    """
    user_ip = IPAttemptLog.query.filter_by(ip_address=client_ip).first()
    if not user_ip:
        user_ip = IPAttemptLog(ip_address=client_ip, recovery_attempts_count=3)
        db.session.add(user_ip)
        db.session.commit()
    return user_ip

def decrement_recovery_attempts(ip_log: IPAttemptLog) -> int:
    """
    Уменьшает счётчик recovery_attempts_count на 1 (но не ниже 0).
    Сохраняет изменения в БД.
    Возвращает обновлённое значение счётчика.
    """
    if ip_log.recovery_attempts_count > 0:
        ip_log.recovery_attempts_count -= 1
        db.session.commit()
    return ip_log.recovery_attempts_count


def bind_ip_to_user_and_reset_attempts(user):
    """
    Привязывает текущий IP к пользователю и сбрасывает счётчик попыток до 3.
    Вызывается при:
      - успешной смене пароля,
      - успешном входе после восстановления.
    """
    client_ip = get_client_ip()
    if not client_ip:
        return  # или логировать

    ip_log = get_or_create_ip_log(client_ip)
    ip_log.user_id = user.id
    ip_log.recovery_attempts_count = 3  # ← всегда сбрасываем при успехе
    db.session.commit()


def update_ip_log_with_user_agent(client_ip: str):
    """
    Обновляет запись IPAttemptLog для указанного IP, сохраняя User-Agent из текущего запроса.
    Если записи нет — создаёт её с recovery_attempts_count=3.
    """
    ip_log = IPAttemptLog.query.filter_by(ip_address=client_ip).first()
    if not ip_log:
        # Создаём новую запись, если не существует
        ip_log = IPAttemptLog(
            ip_address=client_ip,
            recovery_attempts_count=3
        )
        db.session.add(ip_log)

    ip_log.user_agent = request.headers.get('User-Agent')

    db.session.commit()