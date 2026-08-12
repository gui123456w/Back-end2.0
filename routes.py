from flask import Blueprint
from flask import render_template
from flask import request
from flask import redirect
from flask import session
from flask import flash

from database import db

from models import Usuarios
from models import Locais
from models import TiposMaterial
from models import LocaisMateriais


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