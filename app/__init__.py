from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from dotenv import load_dotenv
from app.config import Config
from flask_mail import Mail
from app.extensions import db, mail

load_dotenv()
mail = Mail()

db = SQLAlchemy()
login = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/app.db')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    mail.init_app(app)

    db.init_app(app)
    login.init_app(app)

    from app.routes import routes as main_routes
    app.register_blueprint(main_routes)

    from apscheduler.schedulers.background import BackgroundScheduler
    from app.utils import send_event_reminders

    scheduler = BackgroundScheduler()
    scheduler.add_job(send_event_reminders, 'interval', hours=1)
    scheduler.start()
    
    return app