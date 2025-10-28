from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Collaborator(Base):
    __tablename__ = "collaborators"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sales = relationship("Sale", back_populates="collaborator", cascade="all, delete-orphan")

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True)
    collaborator_id = Column(Integer, ForeignKey("collaborators.id"), nullable=False)
    client_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)  # valor da venda (R$)
    client_first_payment_date = Column(Date, nullable=False)  # data do pagamento da 1ª parcela do cliente
    created_at = Column(DateTime, default=datetime.utcnow)

    collaborator = relationship("Collaborator", back_populates="sales")
    installments = relationship("CommissionInstallment", back_populates="sale", cascade="all, delete-orphan")

class CommissionInstallment(Base):
    __tablename__ = "installments"
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    index = Column(Integer, nullable=False)  # 1,2 ou 3
    client_due_date = Column(Date, nullable=False)  # data do pagamento do cliente para essa parcela
    client_paid = Column(Boolean, default=False)
    client_paid_date = Column(Date, nullable=True)

    collaborator_receipt_date = Column(Date, nullable=True)  # calculado quando client_paid True
    collaborator_paid = Column(Boolean, default=False)  # quando o colaborador efetivamente recebeu
    collaborator_paid_date = Column(Date, nullable=True)

    amount = Column(Float, nullable=False)  # valor que será pago ao colaborador nessa parcela (já respeitando os %)

    sale = relationship("Sale", back_populates="installments")
