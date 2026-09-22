import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Cargar las variables del .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Motor de conexión a PostgreSQL. Sin esto, SQLAlchemy usa sus defaults (pool_size=5,
# max_overflow=10, sin pre_ping, sin recycle) -- contra un pooler como el de Supabase, que cierra
# conexiones idle, eso revienta con OperationalError/SSLError justo cuando llega una ráfaga
# después de un rato de calma (ej. todos los atletas de un box marcando series a la misma hora).
# pool_pre_ping hace un SELECT 1 barato antes de reusar una conexión y la descarta si ya murió,
# en vez de fallar la petición del usuario con ese error.
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800,  # 30 min -- cómodamente por debajo de cualquier timeout de idle del pooler
)

# ¡ESTA ES LA LÍNEA QUE PYTHON NO ENCONTRABA!
# expire_on_commit=False: por default, SQLAlchemy expira TODOS los atributos de un objeto justo
# después de cada commit() -- el primer acceso a cualquier atributo después de eso (ej. Pydantic
# serializando la respuesta con from_attributes=True) dispara un SELECT extra para recargarlo,
# aunque el valor ya esté correcto en memoria (lo acabamos de asignar nosotros). Es seguro
# desactivarlo en esta app: ningún default/onupdate se calcula del lado de la base de datos sin
# que Python ya lo sepa (default=uuid.uuid4, default=datetime.utcnow, server_default="false"/"0"
# siempre acompañados de su default= de Python equivalente) -- ver models.py. Cada request sigue
# teniendo su propia Session, cerrada al final (get_db), así que no hay riesgo de servir datos
# obsoletos entre requests distintos.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: una sesión por request, cerrada siempre al final (éxito o error)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()