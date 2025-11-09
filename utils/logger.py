import os
import logging
from logging.handlers import RotatingFileHandler


import os
import logging
from logging.handlers import RotatingFileHandler


def app_loggers(app):
    """Настраивает три основных логгера: auth, product, system."""
    log_dir = app.config.get('LOG_DIR', 'logs')
    max_bytes = app.config.get('LOG_MAX_BYTES', 10 * 1024 * 1024)  # 10 MB
    backup_count = app.config.get('LOG_BACKUP_COUNT', 5)
    log_level_name = app.config.get('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_name)

    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Только три нужные категории
    loggers_config = {
        'auth': 'auth.log',
        'product': 'product.log',
        'system': 'system.log'
    }

    for name, filename in loggers_config.items():
        logger = logging.getLogger(f"app.{name}")
        logger.setLevel(log_level)

        # Добавляем хендлер только если его ещё нет
        if not logger.handlers:
            handler = RotatingFileHandler(
                os.path.join(log_dir, filename),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            handler.setFormatter(formatter)
            handler.setLevel(log_level)
            logger.addHandler(handler)

        logger.propagate = False