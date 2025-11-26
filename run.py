from flask import Flask, jsonify, request, g, make_response, redirect, url_for
from flask_jwt_extended import unset_jwt_cookies
from routes.product.routes_api import api_bp
from routes.auth.routes_auth import auth_bp
from routes.main.routes_index import main_bp
from routes.admin.routes_ui import admin_bp
from routes.admin.routes_system import admin_system_bp
from routes.staff.routes import staff_bp
from routes.product.routes_ui import product_bp
from routes.user.routes_ui import user_ui_bp
from routes.user.routes_api import user_api_bp
from routes.chat.routes_api import chat_bp
from routes.chat.routes_ui import chat_ui_bp
from routes.qa_engineer.qa import qa_bp
from extensions import mail, jwt, db, migrate
from config.config import Config
from utils.logger import app_loggers
from models import IPAttemptLog, User
from utils.user_sessions import get_safe_user_id


# === PUBLIC ENDPOINTS ===
PUBLIC_ENDPOINTS = {
    # Публичный контент
    'main.index',
    'main.product_page',

    # Публичные API
    'api.get_all_products', 
    'api.get_product_by_id', 

    # Аутентификация и восстановление
    'session.login',
    'session.register',
    'session.reset_password_',
    'session.reset_password_with_token',
    'session.confirm_email',

    # Статика
    'static',
}


def create_app():
    """
    Создаёт и настраивает экземпляр Flask-приложения.

    Инициализирует расширения (БД, миграции, почта, JWT),
    регистрирует blueprint'ы и устанавливает глобальные хуки.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    jwt.init_app(app)

    app_loggers(app)

    # Регистрация blueprint'ов
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_system_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(user_ui_bp) 
    app.register_blueprint(user_api_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(chat_ui_bp)
    app.register_blueprint(qa_bp)
 

    @app.before_request
    def block_blocked_ips():
        """
        Проверяет, заблокирован ли IP-адрес клиента на уровне приложения.

        Перед каждым входящим запросом функция извлекает IP-адрес клиента
        через `request.remote_addr`, ищет соответствующую запись в таблице
        `IPAttemptLog` и, если запись существует и флаг `is_blocked` установлен
        в `True`, немедленно прерывает обработку запроса с HTTP-статусом 403.

        Примечание:
            - Функция предназначена исключительно для демонстрации логики
              блокировки IP-адресов на уровне приложения. В реальной
              эксплуатации эта блокировка будет реализовываться
              на уровне reverse proxy (например, nginx), что обеспечит
              более высокую производительность и защиту на более раннем
              этапе обработки запроса. В будущем проверка может быть
              полностью перенесена в конфигурацию reverse proxy, а данный
              код — удалён.

        Возвращает:
            Response: JSON-ответ с сообщением об ошибке и статусом 403,
                    если IP заблокирован. В противном случае — ничего
                    (запрос продолжает обработку).
        """
        client_ip = request.remote_addr
        if client_ip:
            ip_log = IPAttemptLog.query.filter_by(ip_address=client_ip).first()
            if ip_log and ip_log.is_blocked:
                return jsonify({"error": "Ваш IP-адрес заблокирован."}), 403

    @app.before_request
    def require_authentication():
        """
        Глобальная проверка аутентификации.
        - Публичные endpoint'ы (в PUBLIC_ENDPOINTS) пропускаются без проверки.
        - Все остальные требуют валидной JWT-сессии.
        """
        if request.endpoint in PUBLIC_ENDPOINTS:
            return

        user_id = get_safe_user_id()
        if user_id is None:
            # Определяем, является ли запрос API (все остальные API — приватные)
            if request.endpoint and '.' in request.endpoint:
                return jsonify({"error": "Unauthorized", "message": "Требуется аутентификация"}), 401
            else:
                # HTML-страница
                response = make_response(redirect(url_for('session.login')))
                unset_jwt_cookies(response)
                return response

        try:
            user_id = int(user_id)
            user = db.session.get(User, user_id)
            if not user:
                raise ValueError("User not found in DB")
        except (TypeError, ValueError):
            response = make_response(redirect(url_for('session.login')))
            unset_jwt_cookies(response)
            return response

        g.current_user = user
        g.current_user_id = user_id

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
    # app.run(debug=True)
