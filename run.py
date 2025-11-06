from flask import Flask
import os
from routes.product.routes_api import api_bp
from routes.auth.routes_auth import auth_bp
from routes.main.routes_index import main_bp
from routes.admin.routes import admin_bp
from routes.staff.routes import staff_bp
from routes.product.routes_ui import product_bp
from routes.user.routes_ui import user_ui_bp
from routes.user.routes_api import user_api_bp

from extensions import mail, jwt, db, migrate
from config.config import Config, INSTANCE_DIR


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    jwt.init_app(app)

    # Регистрация маршрутов blueprint
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(user_ui_bp) 
    app.register_blueprint(user_api_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
