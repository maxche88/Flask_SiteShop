import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')

JWT_CONFIG = {
    'JWT_SECRET_KEY': SECRET_KEY,
    'JWT_TOKEN_LOCATION': ['cookies'],   # устанавливаем токены в cookie
    'JWT_COOKIE_SECURE': False,          # отключаем требование https (локально)
    'JWT_COOKIE_SAMESITE': 'Lax',        # разрешаем передачу кук между доменами
    'JWT_ACCESS_COOKIE_NAME': 'access_token',  
    'JWT_REFRESH_COOKIE_NAME': 'refresh_token_cookie',
    'JWT_COOKIE_CSRF_PROTECT': False,     # включаем защиту от CSRF
    'JWT_ACCESS_COOKIE_PATH': '/',       # путь к access токену
    'JWT_REFRESH_COOKIE_PATH': '/token/refresh',  # путь к refresh токену
    'JWT_ACCESS_TOKEN_EXPIRES': 3600,   # срок жизни токена (1 час)
}