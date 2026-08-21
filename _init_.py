import os
from flask import Flask
from dotenv import load_dotenv

from config import Config

from database import db
from extensions import mail


def create_app():

    base_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(base_dir, ".env")
    load_dotenv(dotenv_path)

    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    if not app.config["SECRET_KEY"]:
        raise RuntimeError(
            "SECRET_KEY não encontrada no arquivo .env"
        )

    db.init_app(app)
    mail.init_app(app)

    from routes import main
    app.register_blueprint(main)

    return app
