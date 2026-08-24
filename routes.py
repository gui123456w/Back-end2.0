from flask import Blueprint,render_template,request, redirect,session,flash,url_for

from datetime import datetime, timedelta
import secrets

from flask_mail import Message

from database import db

from models import (
    Usuarios,
    RecuperacaoSenha,
    TermosAceite
)

from extensions import mail


main = Blueprint("main", __name__)

VERSAO_TERMOS = "1.0"


# ============================================================
# VERIFICAÇÃO DOS TERMOS DE USO
# ============================================================

@main.before_request
def verificar_acesso_termos():

    # Rotas que podem ser acessadas sem aceitar os termos.
    # Login, cadastro e recuperação não dependem do aceite.
    rotas_liberadas = {
        "main.index",
        "main.loguin",
        "main.cadastro",
        "main.recuperar_senha",
        "main.redefinir_senha",
        "main.termos_de_uso",
        "main.aceitar_termos",
        "main.logout"
    }

    # Se a rota atual está liberada, não faz nada.
    if request.endpoint in rotas_liberadas:
        return

    # Se o usuário não está logado,
    # não verifica os termos.
    if "usuarios_id_usuario" not in session:
        return

    # ID do usuário logado.
    id_usuario = session[
        "usuarios_id_usuario"
    ]

    # Procura o aceite da versão atual.
    aceite = TermosAceite.query.filter_by(
        id_usuario=id_usuario,
        versao=VERSAO_TERMOS
    ).first()

    # Se ainda não aceitou a versão atual,
    # manda o usuário para os Termos.
    if not aceite:

        return redirect(
            url_for("main.termos_de_uso")
        )


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@main.route("/")
def index():

    # Se não estiver logado,
    # vai para o login.
    if "usuarios_id_usuario" not in session:

        return redirect(
            url_for("main.loguin")
        )

    # Usuário logado vai para a página PI.
    return redirect(
        url_for("main.pi")
    )


# ============================================================
# PÁGINAS INSTITUCIONAIS
# ============================================================

@main.route("/pi")
def pi():

    return render_template(
        "PI.html"
    )


@main.route("/dicas")
def dicas():

    return render_template(
        "Dicas.html"
    )


@main.route("/coleta")
def coleta():

    return render_template(
        "Coleta.html"
    )


# ============================================================
# CADASTRO
# ============================================================

@main.route(
    "/cadastro",
    methods=["GET", "POST"]
)
def cadastro():

    if request.method == "POST":

        # ----------------------------------------------------
        # DADOS DO FORMULÁRIO
        # ----------------------------------------------------

        nome = request.form.get(
            "nome",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        senha = request.form.get(
            "senha",
            ""
        )

        confirmar_senha = request.form.get(
            "confirmar_senha",
            ""
        )

        cpf_bruto = request.form.get(
            "cpf",
            ""
        ).strip()

        cpf = "".join(
            filter(
                str.isdigit,
                cpf_bruto
            )
        )

        # ----------------------------------------------------
        # ACEITE DOS TERMOS
        # ----------------------------------------------------

        aceitar_termos = request.form.get(
            "aceitar_termos"
        )

        if not aceitar_termos:

            flash(
                "Você precisa aceitar os Termos de Uso "
                "para criar sua conta."
            )

            return redirect(
                url_for("main.cadastro")
            )

        # ----------------------------------------------------
        # CAMPOS OBRIGATÓRIOS
        # ----------------------------------------------------

        if (
            not nome
            or not email
            or not senha
            or not cpf
        ):

            flash(
                "Preencha todos os campos."
            )

            return redirect(
                url_for("main.cadastro")
            )

        # ----------------------------------------------------
        # CONFIRMAÇÃO DA SENHA
        # ----------------------------------------------------

        if senha != confirmar_senha:

            flash(
                "As senhas não conferem."
            )

            return redirect(
                url_for("main.cadastro")
            )

        # ----------------------------------------------------
        # TAMANHO DA SENHA
        # ----------------------------------------------------

        if len(senha) < 8:

            flash(
                "A senha deve possuir pelo menos 8 caracteres."
            )

            return redirect(
                url_for("main.cadastro")
            )

        # ----------------------------------------------------
        # CPF
        # ----------------------------------------------------

        if len(cpf) != 11:

            flash(
                "CPF inválido. Digite 11 números."
            )

            return redirect(
                url_for("main.cadastro")
            )

        # ----------------------------------------------------
        # EMAIL DUPLICADO
        # ----------------------------------------------------

        usuario_email = Usuarios.query.filter_by(
            email=email
        ).first()

        if usuario_email:

            flash(
                "Este email já está cadastrado."
            )

            return redirect(
                url_for("main.cadastro")
            )

        # ----------------------------------------------------
        # CPF DUPLICADO
        # ----------------------------------------------------

        usuario_cpf = Usuarios.query.filter_by(
            cpf=cpf
        ).first()

        if usuario_cpf:

            flash(
                "Este CPF já está cadastrado."
            )

            return redirect(
                url_for("main.cadastro")
            )

        # ----------------------------------------------------
        # CRIA USUÁRIO
        # ----------------------------------------------------

        novo = Usuarios(
            nome=nome,
            email=email,
            cpf=cpf
        )

        # Cria senha criptografada.
        novo.criar_senha(senha)

        try:

            # Adiciona o usuário.
            db.session.add(novo)

            # Gera o ID do usuário sem fazer commit ainda.
            db.session.flush()

            # ------------------------------------------------
            # SALVA O ACEITE DOS TERMOS
            # ------------------------------------------------

            novo_aceite = TermosAceite(
                id_usuario=novo.id_usuario,
                versao=VERSAO_TERMOS,
                ip=request.remote_addr
            )

            db.session.add(
                novo_aceite
            )

            # Salva usuário + aceite juntos.
            db.session.commit()

        except Exception as erro:

            # Se qualquer coisa der errado,
            # desfaz o cadastro inteiro.
            db.session.rollback()

            print(
                "Erro ao realizar cadastro:",
                erro
            )

            flash(
                "Não foi possível realizar o cadastro. "
                "Tente novamente."
            )

            return redirect(
                url_for("main.cadastro")
            )

        # ----------------------------------------------------
        # CADASTRO CONCLUÍDO
        # ----------------------------------------------------

        flash(
            "Cadastro realizado com sucesso. "
            "Agora faça login."
        )

        return redirect(
            url_for("main.loguin")
        )

    return render_template(
        "cadastro.html"
    )


# ============================================================
# LOGIN
# ============================================================

@main.route(
    "/loguin",
    methods=["GET", "POST"]
)
def loguin():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        senha = request.form.get(
            "senha",
            ""
        )

        usuario = Usuarios.query.filter_by(
            email=email
        ).first()

        # ----------------------------------------------------
        # VERIFICA LOGIN
        # ----------------------------------------------------

        if usuario and usuario.verificar_senha(senha):

            # Cria sessão.
            session["usuarios_id_usuario"] = (
                usuario.id_usuario
            )

            session["usuarios_nome"] = (
                usuario.nome
            )

            # Vai para o index.
            # O before_request verifica os termos.
            return redirect(
                url_for("main.index")
            )

        flash(
            "Email ou senha inválidos."
        )

    return render_template(
        "loguin.html"
    )


# ============================================================
# RECUPERAÇÃO DE SENHA
# ============================================================

@main.route(
    "/recuperar-senha",
    methods=["GET", "POST"]
)
def recuperar_senha():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        usuario = Usuarios.query.filter_by(
            email=email
        ).first()

        if usuario:

            # ------------------------------------------------
            # GERA TOKEN
            # ------------------------------------------------

            token = secrets.token_urlsafe(64)

            # Token válido por 15 minutos.
            expiracao = (
                datetime.now()
                + timedelta(minutes=15)
            )

            # ------------------------------------------------
            # CRIA REGISTRO
            # ------------------------------------------------

            recuperacao = RecuperacaoSenha(
                id_usuario=usuario.id_usuario,
                token=token,
                expiracao=expiracao,
                usado=False
            )

            db.session.add(
                recuperacao
            )

            db.session.commit()

            # ------------------------------------------------
            # LINK DE RECUPERAÇÃO
            # ------------------------------------------------

            link = (
                request.host_url.rstrip("/")
                + url_for(
                    "main.redefinir_senha",
                    token=token
                )
            )

            # ------------------------------------------------
            # ENVIA EMAIL
            # ------------------------------------------------

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

            try:

                mail.send(
                    mensagem
                )

            except Exception as erro:

                print(
                    "Erro ao enviar email:",
                    erro
                )

                # Remove o token criado
                # caso o envio falhe.
                db.session.delete(
                    recuperacao
                )

                db.session.commit()

                flash(
                    "Não foi possível enviar o email "
                    "de recuperação. Tente novamente mais tarde."
                )

                return redirect(
                    url_for(
                        "main.recuperar_senha"
                    )
                )

        # Não informa se o email existe.
        flash(
            "Se o e-mail estiver cadastrado, "
            "você receberá um link para recuperação."
        )

        return redirect(
            url_for("main.loguin")
        )

    return render_template(
        "recuperar_senha.html"
    )


# ============================================================
# REDEFINIR SENHA
# ============================================================

@main.route(
    "/redefinir-senha/<token>",
    methods=["GET", "POST"]
)
def redefinir_senha(token):

    # --------------------------------------------------------
    # PROCURA TOKEN
    # --------------------------------------------------------

    recuperacao = RecuperacaoSenha.query.filter_by(
        token=token,
        usado=False
    ).first()

    if not recuperacao:

        flash(
            "O link de recuperação é inválido "
            "ou já foi utilizado."
        )

        return redirect(
            url_for("main.recuperar_senha")
        )

    # --------------------------------------------------------
    # VERIFICA EXPIRAÇÃO
    # --------------------------------------------------------

    if datetime.now() > recuperacao.expiracao:

        flash(
            "O link de recuperação expirou."
        )

        return redirect(
            url_for("main.recuperar_senha")
        )

    # --------------------------------------------------------
    # BUSCA USUÁRIO
    # --------------------------------------------------------

    usuario = Usuarios.query.get(
        recuperacao.id_usuario
    )

    if not usuario:

        flash(
            "Usuário não encontrado."
        )

        return redirect(
            url_for("main.recuperar_senha")
        )

    # --------------------------------------------------------
    # ALTERAÇÃO DA SENHA
    # --------------------------------------------------------

    if request.method == "POST":

        nova_senha = request.form.get(
            "senha",
            ""
        )

        confirmar_senha = request.form.get(
            "confirmar_senha",
            ""
        )

        # ----------------------------------------------------
        # CAMPOS VAZIOS
        # ----------------------------------------------------

        if not nova_senha or not confirmar_senha:

            flash(
                "Preencha todos os campos."
            )

            return render_template(
                "redefinir_senha.html",
                token=token
            )

        # ----------------------------------------------------
        # SENHAS DIFERENTES
        # ----------------------------------------------------

        if nova_senha != confirmar_senha:

            flash(
                "As senhas não são iguais."
            )

            return render_template(
                "redefinir_senha.html",
                token=token
            )

        # ----------------------------------------------------
        # SENHA CURTA
        # ----------------------------------------------------

        if len(nova_senha) < 8:

            flash(
                "A senha deve possuir pelo menos 8 caracteres."
            )

            return render_template(
                "redefinir_senha.html",
                token=token
            )

        # ----------------------------------------------------
        # CRIA NOVA SENHA
        # ----------------------------------------------------

        usuario.criar_senha(
            nova_senha
        )

        # Marca token como usado.
        recuperacao.usado = True

        db.session.commit()

        flash(
            "Senha alterada com sucesso!"
        )

        return redirect(
            url_for("main.loguin")
        )

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

    return redirect(
        url_for("main.loguin")
    )


# ============================================================
# TERMOS DE USO
# ============================================================

@main.route("/termos-de-uso")
def termos_de_uso():

    # Os termos podem ser visualizados
    # mesmo sem login.
    #
    # Isso permite que o usuário leia os termos
    # através do link existente no cadastro.

    return render_template(
        "termos_de_uso.html",
        versao=VERSAO_TERMOS
    )


# ============================================================
# ACEITAR TERMOS
# ============================================================

@main.route(
    "/aceitar-termos",
    methods=["POST"]
)
def aceitar_termos():

    # Esta rota é utilizada principalmente
    # para usuários antigos ou para uma nova
    # versão dos termos.

    if "usuarios_id_usuario" not in session:

        return redirect(
            url_for("main.loguin")
        )

    id_usuario = session[
        "usuarios_id_usuario"
    ]

    # --------------------------------------------------------
    # VERIFICA SE JÁ ACEITOU
    # --------------------------------------------------------

    aceite_existente = (
        TermosAceite.query
        .filter_by(
            id_usuario=id_usuario,
            versao=VERSAO_TERMOS
        )
        .first()
    )

    # --------------------------------------------------------
    # SALVA ACEITE
    # --------------------------------------------------------

    if not aceite_existente:

        novo_aceite = TermosAceite(
            id_usuario=id_usuario,
            versao=VERSAO_TERMOS,
            ip=request.remote_addr
        )

        try:

            db.session.add(
                novo_aceite
            )

            db.session.commit()

        except Exception as erro:

            db.session.rollback()

            print(
                "Erro ao salvar aceite dos termos:",
                erro
            )

            flash(
                "Não foi possível registrar "
                "o aceite dos Termos de Uso."
            )

            return redirect(
                url_for("main.termos_de_uso")
            )

    flash(
        "Termos de Uso aceitos com sucesso."
    )

    return redirect(
        url_for("main.pi")
    )


# ============================================================
# FUNÇÃO AUXILIAR
# ============================================================

def verificar_termos_aceitos():

    if "usuarios_id_usuario" not in session:

        return False

    id_usuario = session[
        "usuarios_id_usuario"
    ]

    aceite = (
        TermosAceite.query
        .filter_by(
            id_usuario=id_usuario,
            versao=VERSAO_TERMOS
        )
        .first()
    )

    return aceite is not None