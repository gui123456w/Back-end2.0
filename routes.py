from flask import Blueprint
from flask import render_template
from flask import request
from flask import redirect
from flask import session
from flask import flash
from flask import url_for
from flask import current_app
from datetime import datetime, timedelta
import secrets

from flask_mail import Message

from database import db

from models import Usuarios
from models import Locais
from models import TiposMaterial
from models import LocaisMateriais
from models import RecuperacaoSenha

from extensions import mail

main = Blueprint("main", __name__)



@main.route("/")
def index():

    if "usuarios_id_usuario" not in session:
        return redirect("/login")

    return render_template(
        "index.html",
        usuarios=session["usuarios_nome"]
    )


@main.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    current_app.secret_key = "chave_forçada_123"
    
    if request.method == "POST":

        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        cpf_bruto = request.form.get("cpf", "").strip()
        cpf = "".join(filter(str.isdigit, cpf_bruto))


        if not nome or not email or not senha or not cpf:
            flash("Preencha todos os campos.")
            return redirect("/cadastro")


        if len(cpf) != 11:
            flash("CPF inválido. Digite 11 números.")
            return redirect("/cadastro")

        usuario_email = Usuarios.query.filter_by(email=email).first()

        if usuario_email:
            flash("Este email já está cadastrado.")
            return redirect("/cadastro")

        usuario_cpf = Usuarios.query.filter_by(cpf=cpf).first()

        if usuario_cpf:
            flash("Este CPF já está cadastrado.")
            return redirect("/cadastro")


        novo = Usuarios(
            nome=nome,
            email=email,
            cpf=cpf
        )


        novo.criar_senha(senha)

        db.session.add(novo)
        db.session.commit()

        flash("Cadastro realizado com sucesso.")

        return redirect("/login")

    return render_template("cadastro.html")

@main.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        usuarios = Usuarios.query.filter_by(
            email=email
        ).first()

        if usuarios and usuarios.verificar_senha(senha):

            session["usuarios_id_usuario"] = usuarios.id_usuario
            session["usuarios_nome"] = usuarios.nome

            return redirect("/")

        flash("Email ou senha inválidos.")

    return render_template("login.html")


@main.route("/recuperar-senha", methods=["GET", "POST"])
def recuperar_senha():

    if request.method == "POST":

        email = request.form["email"].strip().lower()

        usuario = Usuarios.query.filter_by(
            email=email
        ).first()

        if usuario:

            # Gera um token aleatório
            token = secrets.token_urlsafe(64)

            # Token válido por 15 minutos
            expiracao = datetime.now() + timedelta(minutes=15)

            # Cria o registro no banco
            recuperacao = RecuperacaoSenha(
                id_usuario=usuario.id_usuario,
                token=token,
                expiracao=expiracao,
                usado=False
            )

            db.session.add(recuperacao)
            db.session.commit()

            # Cria o link
            link = request.host_url.rstrip("/") + url_for(
                "main.redefinir_senha",
                token=token
            )

            # Cria o email
            mensagem = Message(
                subject="Recuperação de senha - Sustenta+",
                recipients=[usuario.email]
            )

            mensagem.body = f"""
Olá, {usuario.nome}!

Recebemos uma solicitação para redefinir a senha
da sua conta no Sustenta+.

Clique no link abaixo para criar uma nova senha:

{link}

Este link ficará válido por 15 minutos.

Caso você não tenha solicitado a recuperação da senha,
ignore este e-mail.

Atenciosamente,
Equipe Sustenta+
"""

            mail.send(mensagem)

        # Não informa se o email existe ou não
        flash(
            "Se o e-mail estiver cadastrado, "
            "você receberá um link para recuperação."
        )

        return redirect("/login")

    return render_template("recuperar_senha.html")

@main.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):

    # Procura o token no banco
    recuperacao = RecuperacaoSenha.query.filter_by(
        token=token,
        usado=False
    ).first()

    if not recuperacao:

        flash(
            "O link de recuperação é inválido "
            "ou já foi utilizado."
        )

        return redirect("/recuperar-senha")

    # Verifica se o token expirou
    if datetime.now() > recuperacao.expiracao:

        flash("O link de recuperação expirou.")

        return redirect("/recuperar-senha")

    # Busca o usuário
    usuario = Usuarios.query.get(
        recuperacao.id_usuario
    )

    if not usuario:

        flash("Usuário não encontrado.")

        return redirect("/recuperar-senha")

    if request.method == "POST":

        nova_senha = request.form.get(
            "senha",
            ""
        )

        confirmar_senha = request.form.get(
            "confirmar_senha",
            ""
        )

        # Verifica campos vazios
        if not nova_senha or not confirmar_senha:

            flash("Preencha todos os campos.")

            return render_template(
                "redefinir_senha.html",
                token=token
            )

        # Verifica se as senhas são iguais
        if nova_senha != confirmar_senha:

            flash("As senhas não são iguais.")

            return render_template(
                "redefinir_senha.html",
                token=token
            )

        # Verifica tamanho mínimo
        if len(nova_senha) < 8:

            flash(
                "A senha deve possuir pelo menos 8 caracteres."
            )

            return render_template(
                "redefinir_senha.html",
                token=token
            )

        # Cria o hash da nova senha
        usuario.criar_senha(nova_senha)

        # Marca o token como usado
        recuperacao.usado = True

        # Salva no banco
        db.session.commit()

        flash("Senha alterada com sucesso!")

        return redirect("/login")

    return render_template(
        "redefinir_senha.html",
        token=token
    )
    
@main.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


@main.route("/index")
def index_redirect():

    return redirect("locais.html")


@main.route("/locais")
def locais():
    
    if "usuarios_id_usuario" not in session:
        return redirect("/login")

    locais = Locais.query.all()
    
    return render_template(
        "locais.html",
        locais=locais
    )
@main.route("/locais/<int:id>")
def detalhes_local(id):

    if "usuarios_id_usuario" not in session:
        return redirect("/login")

    
    local = Locais.query.get_or_404(id)

    materiais = (
        db.session.query(TiposMaterial)
        .join(
            LocaisMateriais,
            TiposMaterial.id_material == LocaisMateriais.id_material
        )
        .filter(
            LocaisMateriais.id_local == id
        )
        .all()
    )
    return render_template(
        "locais_detalhes.html",
        local=local,
        materiais=materiais,
        
    )
    
@main.route("/reciclar", methods=["GET", "POST"])
def reciclar():

    
    materiais = TiposMaterial.query.order_by(
        TiposMaterial.nome
    ).all()

    locais = []

    if request.method == "POST":

        id_material = request.form.get("id_material")

        locais = (
            db.session.query(Locais)
            .join(
                LocaisMateriais,
                Locais.id_local == LocaisMateriais.id_local
            )
            .filter(
                LocaisMateriais.id_material == id_material
            )
            .all()
        )
    
    return render_template(
        "reciclar.html",
        materiais=materiais,
        locais=locais,
    )