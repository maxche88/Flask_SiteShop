import os
from flask import Flask, jsonify, request
from routes.product.routes_api import api_bp
from routes.auth.routes_auth import auth_bp
from routes.main.routes_index import main_bp
from routes.admin.routes_ui import admin_bp
from routes.admin.routes_system import admin_system_bp
from routes.staff.routes import staff_bp
from routes.product.routes_ui import product_bp
from routes.user.routes_ui import user_ui_bp
from routes.user.routes_api import user_api_bp
from extensions import mail, jwt, db, migrate
from config.config import Config, INSTANCE_DIR
from utils.logger import app_loggers
from models import IPAttemptLog


def create_app():
    """
    Создаёт и настраивает экземпляр Flask-приложения.

    Инициализирует расширения (БД, миграции, почта, JWT),
    регистрирует blueprint'ы и устанавливает глобальные хуки.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    jwt.init_app(app)


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

    return app


if __name__ == '__main__':
    app = create_app()
    app_loggers(app)    
    app.run(host='0.0.0.0', port=5000, debug=True)
    # app.run(debug=True)
