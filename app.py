from flask import Flask
from dotenv import load_dotenv
import os
from api.routes_api import api_bp
from auth.routes_auth import auth_bp
from routes_index import main_bp
from routes_panel_a import admin_bp
from routes_panel_s import session_sa_bp
from routes_panel_u import user_bp

from models import db
import logging
from auth.config_jwt import JWT_CONFIG
from auth.config_mail import ConfigMail
from extensions import mail, jwt, db, migrate
from config import Config

load_dotenv()


SECRET_KEY = os.getenv('SECRET_KEY')

def create_app():
    app_ = Flask(__name__)
    app_.config['SECRET_KEY'] = SECRET_KEY
    app_.config.update(JWT_CONFIG)
    app_.config.from_object(ConfigMail)
    app_.config.from_object(Config)
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
    app_.register_blueprint(session_sa_bp)
    app_.register_blueprint(user_bp)

    return app_


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
