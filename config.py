# Конфигурационные настройки приложения
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Секретный ключ (обязателен для Flask, сессий, JWT и т.д.)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Настройки базы данных
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(basedir, "database.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # отключаем, чтобы не было предупреждений

    # Настройки загрузки файлов
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'data_product')
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

    # Дополнительно: можно добавить максимальный размер файла и т.п.
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB