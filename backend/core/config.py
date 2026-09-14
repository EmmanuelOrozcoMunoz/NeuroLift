import os

from dotenv import load_dotenv

load_dotenv()

# ==========================================
# CONFIGURACIÓN JWT (cargada desde .env, nunca hardcodeada)
# ==========================================
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY no está configurada en el .env. "
        "Genera una con `python -c \"import secrets; print(secrets.token_hex(32))\"` "
        "y agrégala como JWT_SECRET_KEY=... en tu archivo .env."
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 día (antes eran 7 días sin revocación posible)

# En producción (.env: ENVIRONMENT=production) se ocultan /docs, /redoc y el schema OpenAPI:
# expuestos sin autenticación, revelan toda la superficie de la API a cualquiera.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DOCS_ENABLED = ENVIRONMENT != "production"

# CORS: orígenes permitidos configurables desde .env (por defecto, solo el frontend local)
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
    if o.strip()
]
