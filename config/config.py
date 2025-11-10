# config/config.py
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Определяем корень проекта (на уровень выше папки config/)
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

INSTANCE_DIR = os.path.join(basedir, 'instance')
LOG_DIR = os.path.join(INSTANCE_DIR, 'logs')

class Config:
    # === Основной секретный ключ Flask ===
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("Переменная окружения SECRET_KEY не задана. Создайте файл .env")

    # === JWT-настройки ===
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = False          # отключено для локальной разработки
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_ACCESS_COOKIE_NAME = 'access_token'
    JWT_REFRESH_COOKIE_NAME = 'refresh_token_cookie'
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_ACCESS_COOKIE_PATH = '/'
    JWT_REFRESH_COOKIE_PATH = '/token/refresh'
    JWT_ACCESS_TOKEN_EXPIRES = 3600    # 1 час

    # === Время жизни токенов подтверждения и восстановления ===
    # Указывается в МИНУТАХ (удобно для теста: 1 минута, продакшен: 1440 = 24 часа)
    UNCONFIRMED_USER_TTL_MINUTES = 1440
    PASSWORD_RESET_TOKEN_TTL_MINUTES = 30

    # === База данных ===
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(INSTANCE_DIR, 'database.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # === Загрузка файлов ===
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'img', 'products')
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # === Почта ===
    MAIL_SERVER = 'smtp.mail.ru'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    # === Логирование ===
    LOG_DIR = LOG_DIR
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT = 5
    LOG_LEVEL = 'INFO'