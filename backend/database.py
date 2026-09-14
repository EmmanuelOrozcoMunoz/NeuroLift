import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Cargar las variables del .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Motor de conexión a PostgreSQL
engine = create_engine(DATABASE_URL)

# ¡ESTA ES LA LÍNEA QUE PYTHON NO ENCONTRABA!
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: una sesión por request, cerrada siempre al final (éxito o error)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()