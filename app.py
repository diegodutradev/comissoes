from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, extract
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, Collaborator, Sale, CommissionInstallment
from datetime import datetime, date, timedelta

DATABASE_URL = "sqlite:///comissoes.db"
app = Flask(__name__)
app.secret_key = "troque_para_uma_chave_secreta"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.bind = engine
Session = scoped_session(sessionmaker(bind=engine))

# --- Helpers ---
def add_months(orig_date, months):
    year = orig_date.year + (orig_date.month - 1 + months) // 12
    month = (orig_date.month - 1 + months) % 12 + 1
    day = orig_date.day
    while True:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1

def compute_commission_multiplier(amount):
    if amount <= 2000:
        return 1.2
    elif amount <= 4000:
        return 1.4
    else:
        return 1.6

def compute_collaborator_receipt_date(client_paid_date: date):
    if client_paid_date.day <= 5:
        return date(client_paid_date.year, client_paid_date.month, 20)
    else:
        next_month = add_months(client_paid_date, 1)
        return date(next_month.year, next_month.month, 5)

# --- Rotas ---
@app.route("/")
def index():
    db = Session()
    collaborators = db.query(Collaborator).order_by(Collaborator.name).all()
    return render_template("collaborators.html", collaborators=collaborators)

@app.route("/collaborator/new", methods=["POST"])
def collaborator_new():
    name = request.form.get("name")
    phone = request.form.get("phone")
    email = request.form.get("email")
    if not name:
        flash("Nome é obrigatório", "danger")
        return redirect(url_for("index"))
    db = Session()
    c = Collaborator(name=name, phone=phone, email=email)
    db.add(c)
    db.commit()
    flash("Colaborador criado.", "success")
    return redirect(url_for("index"))

@app.route("/collaborator/<int:cid>")
def collaborator_detail(cid):
    db = Session()
    collab = db.query(Collaborator).get(cid)
    if not collab:
        flash("Colaborador não encontrado", "danger")
        return redirect(url_for("index"))

    # Filtro de mês e ano (padrão: mês atual)
    month = request.args.get("month", datetime.now().month, type=int)
    year = request.args.get("year", datetime.now().year, type=int)

    # Pega todas as vendas do colaborador com parcelas pagas nesse mês
    installments = (
        db.query(CommissionInstallment)
        .join(Sale)
        .filter(
            Sale.collaborator_id == cid,
            extract("month", CommissionInstallment.client_paid_date) == month,
            extract("year", CommissionInstallment.client_paid_date) == year,
            CommissionInstallment.client_paid == True
        )
        .all()
    )

    # Calcula total de vendas pagas no mês
    total_vendido = sum(inst.amount for inst in installments)
    percentual = compute_commission_multiplier(total_vendido)
    valor_comissao = round(total_vendido * (percentual - 1), 2)

    # Agrupa vendas do colaborador
    todas_vendas = db.query(Sale).filter(Sale.collaborator_id == cid).all()

    return render_template(
        "collaborator_detail.html",
        collaborator=collab,
        total_vendido=total_vendido,
        percentual=percentual,
        valor_comissao=valor_comissao,
        todas_vendas=todas_vendas,
        month=month,
        year=year
    )

@app.route("/sale/new", methods=["GET","POST"])
def sale_new():
    db = Session()
    if request.method == "GET":
        collaborators = db.query(Collaborator).order_by(Collaborator.name).all()
        return render_template("sale_form.html", collaborators=collaborators)

    collab_id = request.form.get("collaborator_id")
    client_name = request.form.get("client_name")
    amount = float(request.form.get("amount") or 0)
    first_payment_str = request.form.get("client_first_payment_date")

    if not (collab_id and client_name and amount and first_payment_str):
        flash("Preencha todos os campos", "danger")
        return redirect(url_for("sale_new"))

    client_first_payment_date = datetime.strptime(first_payment_str, "%Y-%m-%d").date()

    sale = Sale(
        collaborator_id=int(collab_id),
        client_name=client_name,
        amount=amount,
        client_first_payment_date=client_first_payment_date
    )
    db.add(sale)
    db.flush()

    # cria apenas uma parcela (a do cliente)
    inst = CommissionInstallment(
        sale_id = sale.id,
        index = 1,
        client_due_date = client_first_payment_date,
        amount = amount
    )
    db.add(inst)
    db.commit()

    flash("Venda cadastrada com sucesso.", "success")
    return redirect(url_for("collaborator_detail", cid=collab_id))

@app.route("/installment/<int:inst_id>/mark_client_paid", methods=["POST"])
def mark_client_paid(inst_id):
    db = Session()
    inst = db.query(CommissionInstallment).get(inst_id)
    if not inst:
        flash("Parcela não encontrada", "danger")
        return redirect(url_for("index"))

    date_str = request.form.get("client_paid_date")
    if date_str:
        cp_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        cp_date = date.today()

    inst.client_paid = True
    inst.client_paid_date = cp_date
    inst.collaborator_receipt_date = compute_collaborator_receipt_date(cp_date)

    db.commit()
    flash("Pagamento do cliente registrado.", "success")
    return redirect(request.referrer or url_for("index"))

@app.route("/installment/<int:inst_id>/mark_collaborator_paid", methods=["POST"])
def mark_collaborator_paid(inst_id):
    db = Session()
    inst = db.query(CommissionInstallment).get(inst_id)
    if not inst:
        flash("Parcela não encontrada", "danger")
        return redirect(url_for("index"))

    date_str = request.form.get("collaborator_paid_date")
    if date_str:
        p_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        p_date = date.today()

    inst.collaborator_paid = True
    inst.collaborator_paid_date = p_date
    db.commit()
    flash("Pagamento ao colaborador marcado.", "success")
    return redirect(request.referrer or url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
