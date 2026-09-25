from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.core.config import CORS_ORIGINS, DOCS_ENABLED
from backend.core.logging import security_logger
from backend.core.security import _client_ip, limiter
from backend.database import engine, get_db
from backend import models, storage
from backend.routers import admin, ai, auth, boxes, fitness, groups, mesocycles, plans, sessions, sets, users

# Esto crea las tablas si por alguna razón no existieran en la BD
models.Base.metadata.create_all(bind=engine)
# Ídem para los buckets de Storage (avatares, portadas) — ver backend/storage.py.
storage.ensure_buckets()


app = FastAPI(
    title="NeuroLift API",
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(HTTPException)
async def logging_http_exception_handler(request: Request, exc: HTTPException):
    """Registra intentos de acceso no autorizados (401/403) para poder auditarlos después."""
    if exc.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
        security_logger.warning(
            "%s en %s %s desde %s: %s",
            exc.status_code, request.method, request.url.path, _client_ip(request), exc.detail,
        )
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
app.include_router(users.router)
app.include_router(fitness.router)
app.include_router(groups.router)
app.include_router(mesocycles.router)
app.include_router(sessions.router)
app.include_router(sets.router)
app.include_router(ai.router)
app.include_router(admin.router)
app.include_router(plans.router)


@app.get("/")
def test_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "success", "message": "¡NeuroLift conectado a Supabase exitosamente!"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
