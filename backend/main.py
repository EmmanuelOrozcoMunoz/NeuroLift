from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.core.config import CORS_ORIGINS, DOCS_ENABLED
from backend.core.errors import ErrorDeDominio
from backend.core.logging import security_logger
from backend.core.security import _client_ip, limiter
from backend.database import engine, get_db
from backend import models, storage
from backend.routers import (
    admin,
    ai,
    auth,
    boxes,
    classes,
    fitness,
    groups,
    mesocycles,
    plans,
    ranking,
    sessions,
    sets,
    users,
)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Preparación que antes corría al IMPORTAR este módulo (y por eso importar `backend.main`
    exigía Postgres y red). Ahora solo corre al arrancar el servidor.

    - create_all: crea las tablas que falten. Las migraciones de Alembic asumen que el esquema
      base ya existe (no hay una migración inicial que lo cree), así que un ambiente nuevo lo
      sigue necesitando. Si una migración crea una tabla, debe tolerar que ya exista (ver
      a3b4c5d6e7f8).
    - ensure_buckets: buckets de Supabase Storage (avatares, portadas), idempotente."""
    models.Base.metadata.create_all(bind=engine)
    storage.ensure_buckets()
    yield


app = FastAPI(
    title="NeuroLift API",
    lifespan=lifespan,
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _registrar_acceso_denegado(request: Request, codigo: int, detalle) -> None:
    """Registra intentos de acceso no autorizados (401/403) para poder auditarlos después."""
    if codigo in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
        security_logger.warning(
            "%s en %s %s desde %s: %s", codigo, request.method, request.url.path, _client_ip(request), detalle,
        )


@app.exception_handler(HTTPException)
async def logging_http_exception_handler(request: Request, exc: HTTPException):
    _registrar_acceso_denegado(request, exc.status_code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.exception_handler(ErrorDeDominio)
async def error_de_dominio_handler(request: Request, exc: ErrorDeDominio):
    """Traduce los errores de negocio (core/errors.py) a la respuesta HTTP: mismo código y mismo
    `detail` que daban las HTTPException que reemplazan."""
    _registrar_acceso_denegado(request, exc.status_code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Cabeceras de seguridad HTTP estándar (defensa en profundidad; esta API solo sirve
    JSON, nunca HTML propio, así que un CSP estricto no rompe nada)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


# CORS: orígenes permitidos configurables desde .env (por defecto, solo el frontend local)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(boxes.router)
app.include_router(classes.router)
app.include_router(users.router)
app.include_router(fitness.router)
app.include_router(groups.router)
app.include_router(mesocycles.router)
app.include_router(sessions.router)
app.include_router(sets.router)
app.include_router(ai.router)
app.include_router(admin.router)
app.include_router(plans.router)
app.include_router(ranking.router)


@app.get("/")
def test_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "success", "message": "¡NeuroLift conectado a Supabase exitosamente!"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
