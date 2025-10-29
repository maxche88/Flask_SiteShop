from datetime import datetime, timezone

def current_time():
    """Возвращает текущее время в UTC без микросекунд."""
    return datetime.now(timezone.utc).replace(microsecond=0)
