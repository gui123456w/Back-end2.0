from flask import Blueprint, render_template, request, redirect, session, flash, url_for, current_app
from datetime import datetime, timedelta
import secrets

from flask_mail import Message

from database import db

from models import Usuarios, Locais, TiposMaterial, LocaisMateriais, RecuperacaoSenha

from extensions import mail


main = Blueprint("main", __name__)

@main.route("/")
def index():

    if "usuarios_id_usuario" not in session:
        return redirect(url_for("main.login"))

    return render_template(
        "index.html",
        usuarios=session["usuarios_nome"]
    )


# ============================================================
# CADASTRO
# ============================================================

@main.route("/cadastro", methods=["GET", "POST"])
def cadastro():

    if request.method == "POST":

        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        cpf_bruto = request.form.get("cpf", "").strip()
        cpf = "".join(filter(str.isdigit, cpf_bruto))

        # Verifica campos obrigatórios
        if not nome or not email or not senha or not cpf:

            flash("Preencha todos os campos.")

            return redirect(url_for("main.cadastro"))

        # Verifica CPF
        if len(cpf) != 11:

            flash("CPF inválido. Digite 11 números.")

            return redirect(url_for("main.cadastro"))

        # Verifica e-mail duplicado
        usuario_email = Usuarios.query.filter_by(
            email=email
        ).first()

        if usuario_email:

            flash("Este email já está cadastrado.")

            return redirect(url_for("main.cadastro"))

        # Verifica CPF duplicado
        usuario_cpf = Usuarios.query.filter_by(
            cpf=cpf
        ).first()

        if usuario_cpf:

            flash("Este CPF já está cadastrado.")

            return redirect(url_for("main.cadastro"))

        # Cria usuário
        novo = Usuarios(
            nome=nome,
            email=email,
            cpf=cpf
        )

        # Cria senha criptografada
        novo.criar_senha(senha)

        db.session.add(novo)
        db.session.commit()

        flash("Cadastro realizado com sucesso.")

        return redirect(url_for("main.login"))

    return render_template("cadastro.html")


# ============================================================
# LOGIN
# ============================================================

@main.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        usuario = Usuarios.query.filter_by(
            email=email
        ).first()

        if usuario and usuario.verificar_senha(senha):

            session["usuarios_id_usuario"] = usuario.id_usuario
            session["usuarios_nome"] = usuario.nome

            return redirect(url_for("main.index"))

        flash("Email ou senha inválidos.")

    return render_template("login.html")


# ============================================================
# RECUPERAÇÃO DE SENHA
# ============================================================

@main.route("/recuperar-senha", methods=["GET", "POST"])
def recuperar_senha():

    if request.method == "POST":

        email = request.form["email"].strip().lower()

        usuario = Usuarios.query.filter_by(
            email=email
        ).first()

        if usuario:

            # Gera token
            token = secrets.token_urlsafe(64)

            # Token válido por 15 minutos
            expiracao = datetime.now() + timedelta(minutes=15)

            # Cria registro no banco
            recuperacao = RecuperacaoSenha(
                id_usuario=usuario.id_usuario,
                token=token,
                expiracao=expiracao,
                usado=False
            )

            db.session.add(recuperacao)
            db.session.commit()

            # Cria link de recuperação
            link = request.host_url.rstrip("/") + url_for(
                "main.redefinir_senha",
                token=token
            )

            # Cria mensagem
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

        # Não informa se o e-mail existe
        flash(
            "Se o e-mail estiver cadastrado, "
            "você receberá um link para recuperação."
        )

        return redirect(url_for("main.login"))

    return render_template("recuperar_senha.html")


# ============================================================
# REDEFINIR SENHA
# ============================================================

@main.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):

    # Procura token válido
    recuperacao = RecuperacaoSenha.query.filter_by(
        token=token,
        usado=False
    ).first()

    if not recuperacao:

        flash(
            "O link de recuperação é inválido "
            "ou já foi utilizado."
        )

        return redirect(url_for("main.recuperar_senha"))

    # Verifica expiração
    if datetime.now() > recuperacao.expiracao:

        flash("O link de recuperação expirou.")

        return redirect(url_for("main.recuperar_senha"))

    # Busca usuário
    usuario = Usuarios.query.get(
        recuperacao.id_usuario
    )

    if not usuario:

        flash("Usuário não encontrado.")

        return redirect(url_for("main.recuperar_senha"))

    # Alteração da senha
    if request.method == "POST":

        nova_senha = request.form.get(
            "senha",
            ""
        )

        confirmar_senha = request.form.get(
            "confirmar_senha",
            ""
        )

        # Campos vazios
        if not nova_senha or not confirmar_senha:

            flash("Preencha todos os campos.")

            return render_template(
                "redefinir_senha.html",
                token=token
            )

        # Senhas diferentes
        if nova_senha != confirmar_senha:

            flash("As senhas não são iguais.")

            return render_template(
                "redefinir_senha.html",
                token=token
            )

        # Senha muito curta
        if len(nova_senha) < 8:

            flash(
                "A senha deve possuir pelo menos 8 caracteres."
            )

            return render_template(
                "redefinir_senha.html",
                token=token
            )

        # Cria nova senha
        usuario.criar_senha(nova_senha)

        # Marca token como usado
        recuperacao.usado = True

        # Salva
        db.session.commit()

        flash("Senha alterada com sucesso!")

        return redirect(url_for("main.login"))

    return render_template(
        "redefinir_senha.html",
        token=token
    )


# ============================================================
# LOGOUT
# ============================================================

@main.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("main.login"))


# ============================================================
# REDIRECIONAMENTO /INDEX
# ============================================================

@main.route("/index")
def index_redirect():

    return redirect(url_for("main.locais"))


# ============================================================
# LOCAIS
# ============================================================

@main.route("/locais")
def locais():

    if "usuarios_id_usuario" not in session:

        return redirect(url_for("main.login"))

    locais = Locais.query.all()

    return render_template(
        "locais.html",
        locais=locais
    )


# ============================================================
# DETALHES DO LOCAL
# ============================================================

@main.route("/locais/<int:id>")
def detalhes_local(id):

    if "usuarios_id_usuario" not in session:

        return redirect(url_for("main.login"))

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
        materiais=materiais
    )


@main.route("/reciclar", methods=["GET", "POST"])
def reciclar():

    if "usuarios_id_usuario" not in session:

        return redirect(url_for("main.login"))

    materiais = TiposMaterial.query.order_by(
        TiposMaterial.nome
    ).all()

    locais = []

    if request.method == "POST":

        id_material = request.form.get(
            "id_material"
        )

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
        locais=locais
    )