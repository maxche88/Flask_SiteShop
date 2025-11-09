import os
import logging
from logging.handlers import RotatingFileHandler

_loggers = {}
_initialized = False

def _init_loggers():
    global _loggers, _initialized
    if _initialized:
        return

    from flask import current_app
    config = current_app.config

    log_dir = config['LOG_DIR']
    max_bytes = config['LOG_MAX_BYTES']
    backup_count = config['LOG_BACKUP_COUNT']
    log_level = getattr(logging, config['LOG_LEVEL'])

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    def _create_handler(filename):
        handler = RotatingFileHandler(
            os.path.join(log_dir, filename),
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        handler.setLevel(log_level)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        return handler

    # Категории логов
    categories = {
        'auth': 'auth.log',
        'user': 'user_actions.log',
        'admin': 'admin_actions.log',
        'security': 'security.log',
        'system': 'system.log'
    }

    for name, filename in categories.items():
        logger = logging.getLogger(f"app.{name}")
        if not logger.handlers:
            logger.setLevel(log_level)
            logger.addHandler(_create_handler(filename))
        _loggers[name] = logger

    _initialized = True

def get_auth_logger(): return _loggers['auth'] if _initialized else _init_and_get('auth')
def get_user_logger(): return _loggers['user'] if _initialized else _init_and_get('user')
def get_admin_logger(): return _loggers['admin'] if _initialized else _init_and_get('admin')
def get_security_logger(): return _loggers['security'] if _initialized else _init_and_get('security')
def get_system_logger(): return _loggers['system'] if _initialized else _init_and_get('system')

def _init_and_get(name):
    _init_loggers()
    return _loggers[name]