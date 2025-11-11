from flask import Flask, jsonify, request
import os
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

    # ГЛОБАЛЬНАЯ БЛОКИРОВКА ЗАБЛОКИРОВАННЫХ IP
    @app.before_request
    def block_blocked_ips():
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
