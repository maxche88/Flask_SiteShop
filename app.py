from flask import Flask
from dotenv import load_dotenv
import os
from routes.api.routes_api import api_bp
from routes.auth.routes_auth import auth_bp
from routes.main.routes_index import main_bp
from routes.admin.routes import admin_bp
from routes.staff.routes import suser_bp
from routes.product.routes import product_bp
from routes.user.routes_panel_u import user_bp

from models import db
import logging
from config.config_mail import ConfigMail
from extensions import mail, jwt, db, migrate
from config.config import Config


def create_app():
    app_ = Flask(__name__)
    app_.config.from_object(Config)
    app_.config.from_object(ConfigMail)
    
    db.init_app(app_)
    migrate.init_app(app_, db)
    os.makedirs(app_.config['UPLOAD_FOLDER'], exist_ok=True)
    mail.init_app(app_)
    jwt.init_app(app_)
    logging.getLogger().setLevel(logging.ERROR)


    # Регистрация маршрутов blueprint
    app_.register_blueprint(api_bp)
    app_.register_blueprint(auth_bp)
    app_.register_blueprint(main_bp)
    app_.register_blueprint(admin_bp)
    app_.register_blueprint(product_bp)
    app_.register_blueprint(suser_bp)
    app_.register_blueprint(user_bp)

    return app_


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
