import os
from flask import Flask
from dotenv import load_dotenv

from config import Config
from database import db
from extensions import mail
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Força uma chave secreta diretamente na instância do app
    app.secret_key = app.config.get("SECRET_KEY") or "chave_secreta_provisoria_para_testes_123"

    db.init_app(app)
    mail.init_app(app)

    from routes import main
    app.register_blueprint(main)

    return app