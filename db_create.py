from sqlalchemy import create_engine
from models import Base

def create_db(path="sqlite:///comissoes.db"):
    engine = create_engine(path, echo=False)
    Base.metadata.create_all(engine)
    print("DB criado/atualizado.")
    
if __name__ == "__main__":
    create_db()
