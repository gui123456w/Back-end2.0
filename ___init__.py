import os
from flask import Flask
from dotenv import load_dotenv

from config import Config
from database import db
from extensions import mail


def create_app():

    # Localiza a pasta onde está o __init__.py
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Localiza o .env dentro da pasta do projeto
    dotenv_path = os.path.join(base_dir, ".env")

    # Carrega o .env
    load_dotenv(dotenv_path)

    app = Flask(__name__)

    app.config.from_object(Config)

    # SECRET_KEY
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    # Verifica se a SECRET_KEY foi carregada
    if not app.config["SECRET_KEY"]:
        raise RuntimeError(
            "SECRET_KEY não encontrada no arquivo .env"
        )

    db.init_app(app)
    mail.init_app(app)

    from routes import main
    app.register_blueprint(main)

    return app