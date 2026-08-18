import os
from flask import Flask
from dotenv import load_dotenv

from config import Config
from database import db
from extensions import mail


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    db.init_app(app)
    mail.init_app(app)

    from routes import main
    app.register_blueprint(main)

    return app