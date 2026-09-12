import logging
import os
from fastapi import FastAPI, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, func, case
from typing import List
from uuid import UUID
from datetime import timedelta, datetime, date
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import jwt

from backend.database import SessionLocal, engine
from backend import avatars, models, schemas, fitness_scoring, ai_agent, storage

load_dotenv()

# ==========================================
# LOGGING DE SEGURIDAD (logins fallidos, 401/403, cambios de rol)
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
security_logger = logging.getLogger("neurolift.security")


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "?"


# Esto crea las tablas si por alguna razón no existieran en la BD
models.Base.metadata.create_all(bind=engine)
# Ídem para los buckets de Storage (avatares, portadas) — ver backend/storage.py.
storage.ensure_buckets()

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
_docs_enabled = ENVIRONMENT != "production"

limiter = Limiter(key_func=get_remote_address)


def _redirect_to_image(bucket: str, filename: str | None):
    """Redirige a una URL firmada de corta duración de Supabase Storage — los buckets son
    PRIVADOS, así que esta es la única forma de leer un objeto. Se llama DESPUÉS de que el
    endpoint ya comprobó que quien pregunta tiene permiso de ver esta imagen en particular; la
    firma en sí no vuelve a chequear nada de eso. El navegador sigue la redirección solo, sin
    reenviar el header Authorization (va a otro origen) — no hace falta, la firma ya autoriza."""
    if not filename:
        raise HTTPException(status_code=404, detail="No hay imagen.")
    url = storage.create_signed_url(bucket, filename)
    return RedirectResponse(url, status_code=307)


def _ip_and_user_key(request: Request) -> str:
    """Clave de rate limit por IP + usuario autenticado (no solo IP): decodifica el JWT del
    header Authorization en un intento best-effort — si no hay token válido, usa solo la IP.
    Así un solo usuario no puede evadir el límite cambiando de red, ni una IP compartida
    (oficina, NAT) hace que un usuario agote la cuota de otro."""
    ip = get_remote_address(request)
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        try:
            payload = jwt.decode(auth_header[7:], SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("id")
            if user_id:
                return f"{ip}:{user_id}"
        except jwt.PyJWTError:
            pass
    return f"{ip}:anon"

app = FastAPI(
    title="NeuroLift API",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
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
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Le decimos a FastAPI dónde está la ruta de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    revoked_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Esta sesión fue cerrada. Inicia sesión de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_version = payload.get("tv", 0)
    except jwt.PyJWTError:  # Atrapa tokens expirados o falsificados
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception

    # Revocación real: si el usuario cerró sesión (o un admin forzó la revocación) después de
    # que se emitió este token, su token_version ya avanzó y este token deja de ser válido
    # aunque no haya expirado.
    if token_version != user.token_version:
        raise revoked_exception

    return user


def _optional_current_user(request: Request, db: Session) -> models.User | None:
    """Como get_current_user, pero nunca lanza: /auth/register es público (un atleta se
    auto-registra sin token) y a la vez lo usa un coach YA logueado para dar de alta a sus
    propios atletas (con su token en el header). Si no hay header, o el token es inválido,
    expiró o fue revocado, simplemente se trata como registro anónimo (devuelve None) en vez
    de rechazar la petición."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    try:
        payload = jwt.decode(auth_header[7:], SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        usuario = db.query(models.User).filter(models.User.email == email).first()
        if not usuario or payload.get("tv", 0) != usuario.token_version:
            return None
        return usuario
    except jwt.PyJWTError:
        return None


def require_coach(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Dependencia para endpoints de gestión de coach (el rol 'admin' también pasa: tiene
    visibilidad y control total sobre la app)."""
    if current_user.role not in ("coach", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acción reservada para coaches")
    return current_user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Dependencia para endpoints reservados exclusivamente al rol 'admin'."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acción reservada para administradores")
    return current_user


def _coach_athlete_ids(db: Session, coach_id: UUID) -> set[UUID]:
    """IDs de los atletas que este coach puede gestionar: los que él registró directamente
    (User.coach_id) más los que son miembros de alguno de sus grupos. Es la definición única
    de "mis atletas" — úsala en vez de reimplementar el criterio en cada endpoint."""
    directos = db.query(models.User.id).filter(models.User.coach_id == coach_id)
    de_grupos = (
        db.query(models.User.id)
        .join(models.group_members, models.group_members.c.user_id == models.User.id)
        .join(models.Group, models.Group.id == models.group_members.c.group_id)
        .filter(models.Group.coach_id == coach_id)
    )
    return {row[0] for row in directos.union(de_grupos).all()}


def ensure_owner_or_coach(db: Session, owner_id: UUID | None, current_user: models.User):
    """Verifica que el usuario autenticado sea el dueño del recurso, un admin, o un coach que
    tenga a `owner_id` entre sus propios atletas (ver _coach_athlete_ids) — ya NO basta con
    "ser coach": cada coach queda limitado a sus propios atletas/grupos."""
    if current_user.role == "admin":
        return
    if owner_id is not None and current_user.id == owner_id:
        return
    if owner_id is not None and current_user.role == "coach" and owner_id in _coach_athlete_ids(db, current_user.id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso sobre este recurso")


@app.get("/")
def test_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "success", "message": "¡NeuroLift conectado a Supabase exitosamente!"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ==========================================
# ENDPOINTS DE AUTENTICACIÓN
# ==========================================
REGISTER_GENERIC_MESSAGE = "Si el correo no estaba registrado, tu cuenta fue creada. Ya puedes iniciar sesión."


@app.post("/auth/register", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
def register_user(request: Request, user: schemas.UserRegister, db: Session = Depends(get_db)):
    """Misma respuesta (mismo status, mismo cuerpo, mismo tiempo aproximado) exista o no ya
    una cuenta con ese correo — evita que alguien use este endpoint para enumerar qué correos
    están registrados en el sistema (ni por el contenido de la respuesta ni por temporización,
    ya que el hasheo bcrypt, intencionalmente lento, se ejecuta siempre)."""
    db_user = db.query(models.User).filter(models.User.email == user.email).first()

    # Siempre se hashea la contraseña, se use o no, para que ambas rutas tarden lo mismo.
    hashed_password = get_password_hash(user.password)

    if not db_user:
        # Si quien llama es un coach YA autenticado (p. ej. desde "Registrar atleta" en su
        # propio panel), el atleta nuevo queda vinculado a él automáticamente — así aparece de
        # inmediato entre "sus" atletas. Si es un registro anónimo (el atleta se dio de alta
        # solo), queda sin coach hasta que alguno lo agregue a un grupo o lo reclame.
        creador = _optional_current_user(request, db)
        coach_id = creador.id if (user.role == "athlete" and creador is not None and creador.role == "coach") else None

        nuevo_usuario = models.User(
            email=user.email,
            full_name=user.full_name,
            hashed_password=hashed_password,
            role=user.role,
            body_weight=user.body_weight,
            coach_id=coach_id,
        )
        db.add(nuevo_usuario)
        db.commit()

    return {"message": REGISTER_GENERIC_MESSAGE}


@app.post("/auth/login")
@limiter.limit("10/minute")
def login_user(request: Request, credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    usuario = db.query(models.User).filter(models.User.email == credentials.email).first()

    if not usuario or not verify_password(credentials.password, usuario.hashed_password):
        security_logger.warning("Login fallido para email=%s desde %s", credentials.email, _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    security_logger.info("Login exitoso: %s (rol=%s) desde %s", usuario.email, usuario.role, _client_ip(request))

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": usuario.email, "role": usuario.role, "id": str(usuario.id), "tv": usuario.token_version},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/auth/logout", response_model=schemas.MessageResponse)
def logout_user(
    request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Revoca de verdad el token actual (y cualquier otro que este usuario tuviera emitido en
    otros dispositivos): avanza su token_version, así que ningún token anterior vuelve a
    validar aunque no haya expirado todavía."""
    current_user.token_version += 1
    db.commit()
    security_logger.info("Logout (revocación de tokens): %s desde %s", current_user.email, _client_ip(request))
    return {"message": "Sesión cerrada. Todos los tokens emitidos antes de ahora quedaron revocados."}


# --- ENDPOINTS PARA USUARIOS ---

@app.get("/users/", response_model=List[schemas.UserResponse])
def get_users(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Listado global de usuarios (todos los roles): solo un admin lo necesita — un coach ya
    tiene su propio listado acotado en GET /users/athletes."""
    return db.query(models.User).all()


@app.get("/users/athletes", response_model=List[schemas.UserResponse])
def get_athletes(db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    """Los atletas del coach autenticado (los que él registró + los de sus grupos) para su menú
    desplegable. Un admin sigue viendo a todos."""
    if current_user.role == "admin":
        return db.query(models.User).filter(models.User.role == "athlete").all()
    ids = _coach_athlete_ids(db, current_user.id)
    if not ids:
        return []
    return db.query(models.User).filter(models.User.id.in_(ids)).all()


@app.get("/coach/leaderboard", response_model=List[schemas.AthleteActivityResponse])
def get_athlete_leaderboard(db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    """Tabla de posiciones: cuántos entrenamientos completó cada uno de TUS atletas (los que el
    propio atleta marcó como hechos, con sus reps/pesos reales) — antes el coach no tenía forma
    de ver esto sin entrar mesociclo por mesociclo. Ordenado por actividad de esta semana."""
    if current_user.role == "admin":
        ids = {u.id for u in db.query(models.User.id).filter(models.User.role == "athlete").all()}
    else:
        ids = _coach_athlete_ids(db, current_user.id)
    if not ids:
        return []

    atletas = db.query(models.User).filter(models.User.id.in_(ids)).all()

    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # lunes de esta semana

    filas = (
        db.query(
            models.Mesocycle.user_id.label("user_id"),
            func.count(models.Session.id).label("total"),
            func.sum(case((models.Session.completed_date >= inicio_semana, 1), else_=0)).label("esta_semana"),
            func.max(models.Session.completed_date).label("ultima"),
        )
        .join(models.Session, models.Session.mesocycle_id == models.Mesocycle.id)
        .filter(models.Mesocycle.user_id.in_(ids), models.Session.status == "completed")
        .group_by(models.Mesocycle.user_id)
        .all()
    )
    stats_por_atleta = {f.user_id: f for f in filas}

    # Último WOD con resultado registrado, uno por atleta (el más reciente primero en la
    # consulta, así que el primero que aparece por atleta ya es el que queremos).
    sesiones_wod = (
        db.query(models.Session)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .options(joinedload(models.Session.mesocycle), joinedload(models.Session.sets))
        .filter(
            models.Mesocycle.user_id.in_(ids),
            models.Session.status == "completed",
            models.Session.wod_format.isnot(None),
        )
        .order_by(models.Session.completed_date.desc())
        .all()
    )
    ultimo_wod_por_atleta: dict = {}
    for s in sesiones_wod:
        ultimo_wod_por_atleta.setdefault(s.mesocycle.user_id, s)

    resultados = [
        schemas.AthleteActivityResponse(
            user_id=atleta.id,
            full_name=atleta.full_name,
            has_avatar=atleta.has_avatar,
            completed_total=(stats_por_atleta[atleta.id].total if atleta.id in stats_por_atleta else 0),
            completed_this_week=(
                int(stats_por_atleta[atleta.id].esta_semana) if atleta.id in stats_por_atleta else 0
            ),
            last_completed_at=(stats_por_atleta[atleta.id].ultima if atleta.id in stats_por_atleta else None),
            last_wod_summary=_format_wod_summary(ultimo_wod_por_atleta.get(atleta.id)),
        )
        for atleta in atletas
    ]
    resultados.sort(key=lambda r: (r.completed_this_week, r.completed_total), reverse=True)
    return resultados


@app.get("/users/{user_id}/recent-activity", response_model=List[schemas.RecentSessionSummary])
def get_recent_activity(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Últimas 10 sesiones COMPLETADAS de este atleta, con lo que REALMENTE hizo (reps/pesos
    reales por ejercicio, resultado del WOD si tenía uno prescrito) — antes el coach no tenía
    forma de ver esto sin entrar mesociclo por mesociclo."""
    ensure_owner_or_coach(db, user_id, current_user)

    sesiones = (
        db.query(models.Session)
        .join(models.Mesocycle, models.Session.mesocycle_id == models.Mesocycle.id)
        .options(
            joinedload(models.Session.mesocycle),
            joinedload(models.Session.sets).joinedload(models.Set.exercise),
        )
        .filter(models.Mesocycle.user_id == user_id, models.Session.status == "completed")
        .order_by(models.Session.completed_date.desc())
        .limit(10)
        .all()
    )

    resultados = []
    for sesion in sesiones:
        # Agrupa series CONSECUTIVAS del mismo ejercicio+bloque (igual que groupSets en el
        # frontend) — así "Back Squat" con 4 series seguidas se lee como un solo renglón.
        ejercicios: list[schemas.RecentSessionExercise] = []
        for s in sorted(sesion.sets, key=lambda x: x.set_order):
            nombre = s.exercise.name if s.exercise else "Ejercicio"
            anterior = ejercicios[-1] if ejercicios else None
            if anterior and anterior.exercise_name == nombre and anterior.block == s.block:
                fila = anterior
            else:
                fila = schemas.RecentSessionExercise(exercise_name=nombre, block=s.block)
                ejercicios.append(fila)
            if s.actual_reps is not None:
                fila.actual_reps.append(s.actual_reps)
                fila.sets_logged += 1
            if s.actual_weight is not None:
                fila.actual_weight.append(s.actual_weight)

        resultados.append(schemas.RecentSessionSummary(
            session_id=sesion.id,
            scheduled_date=sesion.scheduled_date,
            completed_date=sesion.completed_date,
            mesocycle_name=sesion.mesocycle.name,
            discipline=sesion.mesocycle.discipline,
            wod_format=sesion.wod_format,
            wod_time_seconds=sesion.wod_time_seconds,
            wod_rounds=sesion.wod_rounds,
            wod_extra_reps=sesion.wod_extra_reps,
            wod_emom_completed=sesion.wod_emom_completed,
            exercises=ejercicios,
        ))
    return resultados


@app.get("/users/search", response_model=schemas.UserResponse)
@limiter.limit("30/hour", key_func=_ip_and_user_key)
def search_athlete_by_email(
    request: Request, email: str, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Busca UN atleta por correo EXACTO (case-insensitive) — para que un coach pueda encontrar
    a un atleta que se auto-registró por su cuenta y agregarlo a un grupo, sin exponerle el
    listado completo de usuarios de la plataforma (eso rompería el aislamiento por coach).
    Limitado por hora para que no se use como herramienta de enumeración masiva de correos."""
    usuario = db.query(models.User).filter(
        models.User.role == "athlete", models.User.email.ilike(email.strip())
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="No hay ningún atleta registrado con ese correo.")
    return usuario


_AVATAR_CONTENT_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


@app.post("/users/me/avatar", response_model=schemas.UserResponse)
@limiter.limit("10/hour", key_func=_ip_and_user_key)
async def upload_my_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Sube (o reemplaza) la foto de perfil del usuario autenticado. Solo uno mismo puede
    subir su propia foto — no hay ruta equivalente para que un coach suba la de un atleta."""
    raw = await avatars.read_and_validate_upload(file)
    clean_bytes, extension = avatars.rerender_and_strip_metadata(raw)

    nombre_anterior = current_user.avatar_filename
    nuevo_nombre = storage.upload_object(
        storage.AVATAR_BUCKET, clean_bytes, extension, _AVATAR_CONTENT_TYPES[extension]
    )

    current_user.avatar_filename = nuevo_nombre
    db.commit()
    db.refresh(current_user)

    # Se borra la anterior DESPUÉS de confirmar la nueva en la BD (si algo falla antes, la
    # foto anterior sigue siendo válida en vez de quedar el usuario sin ninguna).
    storage.delete_object(storage.AVATAR_BUCKET, nombre_anterior)

    security_logger.info("Foto de perfil actualizada: %s desde %s", current_user.email, _client_ip(request))
    return current_user


@app.delete("/users/me/avatar", response_model=schemas.MessageResponse)
def delete_my_avatar(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    if not current_user.avatar_filename:
        raise HTTPException(status_code=404, detail="No tienes foto de perfil.")
    storage.delete_object(storage.AVATAR_BUCKET, current_user.avatar_filename)
    current_user.avatar_filename = None
    db.commit()
    return {"message": "Foto de perfil eliminada."}


@app.get("/users/{user_id}/avatar")
def get_user_avatar(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Cualquier usuario autenticado puede ver la foto de perfil de otro (no es información
    sensible más allá del nombre, que ya es visible en toda la app)."""
    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if not usuario or not usuario.avatar_filename:
        raise HTTPException(status_code=404, detail="Este usuario no tiene foto de perfil.")
    return _redirect_to_image(storage.AVATAR_BUCKET, usuario.avatar_filename)


@app.get("/users/{user_id}/mesocycles/")
def obtener_mesociclos_usuario(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    ensure_owner_or_coach(db, user_id, current_user)
    return db.query(models.Mesocycle).filter(models.Mesocycle.user_id == user_id).all()


# Los 4 levantamientos de halterofilia del calculador de Fit Level son, ni más ni menos, un
# 1RM — lo mismo que ya representa una fila de PersonalRecord. Antes vivían aislados en
# fitness_benchmarks (metric_key) sin aparecer nunca en "Récords (PRs)", así que el atleta
# terminaba registrando el mismo número dos veces en dos pantallas distintas. Estos mapeos
# mantienen ambas tablas en sincronía sin importar por cuál pantalla se haya registrado.
_FIT_LEVEL_LIFT_TO_PR_NAME = {
    "snatch_kg": "Snatch",
    "clean_jerk_kg": "Clean & Jerk",
    "back_squat_kg": "Back Squat",
    "deadlift_kg": "Deadlift",
}
_PR_NAME_TO_FIT_LEVEL_LIFT = {name.lower(): key for key, name in _FIT_LEVEL_LIFT_TO_PR_NAME.items()}


def _upsert_personal_record_by_name(db: Session, user_id: UUID, exercise_name: str, max_weight_kg: float) -> None:
    """Como upsert_personal_record, pero para uso interno (sync con Fit Level): busca SIN
    importar mayúsculas/minúsculas, para no crear un duplicado si el ejercicio ya existía escrito
    distinto (p. ej. "back squat" vs "Back Squat")."""
    existente = db.query(models.PersonalRecord).filter(
        models.PersonalRecord.user_id == user_id,
        func.lower(models.PersonalRecord.exercise_name) == exercise_name.lower(),
    ).first()
    if existente:
        existente.max_weight_kg = max_weight_kg
    else:
        db.add(models.PersonalRecord(user_id=user_id, exercise_name=exercise_name, max_weight_kg=max_weight_kg))


@app.post("/users/{user_id}/records/")
def upsert_personal_record(
    user_id: UUID,
    record: schemas.PRCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Añade una nueva marca o la actualiza si el ejercicio ya existe."""
    ensure_owner_or_coach(db, user_id, current_user)
    pr_existente = db.query(models.PersonalRecord).filter(
        models.PersonalRecord.user_id == user_id,
        models.PersonalRecord.exercise_name == record.exercise_name,
    ).first()

    if pr_existente:
        pr_existente.max_weight_kg = record.max_weight_kg
        mensaje = f"RM de {record.exercise_name} actualizado a {record.max_weight_kg}kg"
    else:
        db.add(models.PersonalRecord(
            user_id=user_id, exercise_name=record.exercise_name, max_weight_kg=record.max_weight_kg,
        ))
        mensaje = f"Nuevo RM de {record.exercise_name} registrado."

    # Si el nombre coincide con uno de los 4 levantamientos del Fit Level, esta marca también
    # actualiza esa métrica — así no hay que volver a escribirla en la otra pantalla.
    metric_key = _PR_NAME_TO_FIT_LEVEL_LIFT.get(record.exercise_name.strip().lower())
    if metric_key:
        fila = db.query(models.FitnessBenchmark).filter(
            models.FitnessBenchmark.user_id == user_id, models.FitnessBenchmark.metric_key == metric_key,
        ).first()
        if fila:
            fila.value = record.max_weight_kg
        else:
            db.add(models.FitnessBenchmark(user_id=user_id, metric_key=metric_key, value=record.max_weight_kg))

    db.commit()
    return {"message": mensaje}


@app.get("/users/{user_id}/records/", response_model=List[schemas.PRResponse])
def obtener_marcas_atleta(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    ensure_owner_or_coach(db, user_id, current_user)
    return db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == user_id).all()


# --- ENDPOINTS PARA EL CALCULADOR DE "FIT LEVEL" ---

@app.put("/users/{user_id}/fitness-benchmarks", response_model=schemas.FitnessLevelResponse)
def update_fitness_benchmarks(
    user_id: UUID,
    req: schemas.FitnessBenchmarkUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Guarda las marcas que el atleta (dueño) o su coach hayan llenado, y devuelve el
    Fit Level ya recalculado. Solo se tocan los campos enviados (no None)."""
    ensure_owner_or_coach(db, user_id, current_user)

    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    datos = req.model_dump(exclude_unset=True, exclude_none=True)

    if "body_weight" in datos:
        usuario.body_weight = datos.pop("body_weight")
    if "sex" in datos:
        usuario.sex = datos.pop("sex")
    if "age" in datos:
        usuario.age = datos.pop("age")

    for metric_key, value in datos.items():
        if metric_key not in fitness_scoring.METRICS:
            continue
        valor = float(value)
        fila = db.query(models.FitnessBenchmark).filter(
            models.FitnessBenchmark.user_id == user_id,
            models.FitnessBenchmark.metric_key == metric_key,
        ).first()
        if fila:
            fila.value = valor
        else:
            db.add(models.FitnessBenchmark(user_id=user_id, metric_key=metric_key, value=valor))

        # Los 4 levantamientos de halterofilia también son un RM: que aparezcan en "Récords
        # (PRs)" sin tener que volver a escribirlos ahí a mano.
        nombre_pr = _FIT_LEVEL_LIFT_TO_PR_NAME.get(metric_key)
        if nombre_pr:
            _upsert_personal_record_by_name(db, user_id, nombre_pr, valor)

    db.commit()
    return _build_fitness_level_response(db, usuario)


@app.get("/users/{user_id}/fitness-level", response_model=schemas.FitnessLevelResponse)
def get_fitness_level(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Devuelve las marcas guardadas y el Fit Level calculado a partir de ellas."""
    ensure_owner_or_coach(db, user_id, current_user)
    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _build_fitness_level_response(db, usuario)


def _build_fitness_level_response(db: Session, usuario: models.User) -> schemas.FitnessLevelResponse:
    filas = db.query(models.FitnessBenchmark).filter(models.FitnessBenchmark.user_id == usuario.id).all()
    valores = {f.metric_key: f.value for f in filas}

    # Si algún RM de halterofilia no se llenó nunca desde Fit Level pero sí existe como
    # PersonalRecord (p. ej. lo registró el coach desde "Récords (PRs)" antes de que esta
    # sincronización existiera), se usa ese valor en vez de dejar el campo vacío.
    faltantes = [k for k in _FIT_LEVEL_LIFT_TO_PR_NAME if k not in valores]
    if faltantes:
        prs = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == usuario.id).all()
        prs_por_nombre = {pr.exercise_name.strip().lower(): pr.max_weight_kg for pr in prs}
        for metric_key in faltantes:
            nombre_pr = _FIT_LEVEL_LIFT_TO_PR_NAME[metric_key].lower()
            if nombre_pr in prs_por_nombre:
                valores[metric_key] = prs_por_nombre[nombre_pr]

    resultado = fitness_scoring.compute_fitness_level(valores, usuario.body_weight, usuario.sex, usuario.age)
    return schemas.FitnessLevelResponse(
        body_weight=usuario.body_weight,
        sex=usuario.sex,
        age=usuario.age,
        values=valores,
        category_scores=resultado["category_scores"],
        category_levels=resultado["category_levels"],
        overall_score=resultado["overall_score"],
        overall_level=resultado["overall_level"],
    )


# --- ENDPOINTS PARA GRUPOS DE ATLETAS (coach: solo sus propios grupos; admin: cualquiera) ---

def _get_owned_group(db: Session, group_id: UUID, current_user: models.User) -> models.Group:
    grupo = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if current_user.role != "admin" and grupo.coach_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este grupo no te pertenece")
    return grupo


@app.post("/groups/", response_model=schemas.GroupResponse)
def create_group(
    req: schemas.GroupCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    nuevo_grupo = models.Group(coach_id=current_user.id, name=req.name)
    if req.athlete_ids:
        atletas = db.query(models.User).filter(
            models.User.id.in_(req.athlete_ids), models.User.role == "athlete"
        ).all()
        nuevo_grupo.members = atletas
    db.add(nuevo_grupo)
    db.commit()
    db.refresh(nuevo_grupo)
    return nuevo_grupo


@app.get("/groups/", response_model=List[schemas.GroupSummaryResponse])
def list_my_groups(db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    """Panel del coach: todos sus grupos con el número de atletas en cada uno.
    Si quien pregunta es admin, devuelve TODOS los grupos de TODOS los coaches."""
    query = db.query(models.Group).options(joinedload(models.Group.coach))
    if current_user.role != "admin":
        query = query.filter(models.Group.coach_id == current_user.id)
    grupos = query.all()
    return [
        schemas.GroupSummaryResponse(
            id=g.id, name=g.name, created_at=g.created_at, member_count=len(g.members),
            coach_name=g.coach.full_name, has_cover_image=g.has_cover_image,
        )
        for g in grupos
    ]


@app.get("/groups/{group_id}", response_model=schemas.GroupResponse)
def get_group_detail(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    return _get_owned_group(db, group_id, current_user)


@app.post("/groups/{group_id}/cover", response_model=schemas.GroupResponse)
@limiter.limit("10/hour", key_func=_ip_and_user_key)
async def upload_group_cover(
    request: Request,
    group_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Sube (o reemplaza) la foto de portada del grupo — mismo pipeline de saneo que el avatar
    de usuario (magic-number, re-render sin metadatos, nombre aleatorio)."""
    grupo = _get_owned_group(db, group_id, current_user)
    raw = await avatars.read_and_validate_upload(file)
    clean_bytes, extension = avatars.rerender_and_strip_metadata(raw)

    nombre_anterior = grupo.cover_image_filename
    nuevo_nombre = storage.upload_object(
        storage.GROUP_COVER_BUCKET, clean_bytes, extension, _AVATAR_CONTENT_TYPES[extension]
    )
    grupo.cover_image_filename = nuevo_nombre
    db.commit()
    db.refresh(grupo)
    storage.delete_object(storage.GROUP_COVER_BUCKET, nombre_anterior)
    return grupo


@app.delete("/groups/{group_id}/cover", response_model=schemas.MessageResponse)
def delete_group_cover(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    grupo = _get_owned_group(db, group_id, current_user)
    if not grupo.cover_image_filename:
        raise HTTPException(status_code=404, detail="Este grupo no tiene foto de portada.")
    storage.delete_object(storage.GROUP_COVER_BUCKET, grupo.cover_image_filename)
    grupo.cover_image_filename = None
    db.commit()
    return {"message": "Foto de portada eliminada."}


@app.get("/groups/{group_id}/cover")
def get_group_cover(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    grupo = _get_owned_group(db, group_id, current_user)
    return _redirect_to_image(storage.GROUP_COVER_BUCKET, grupo.cover_image_filename)


def _clone_mesocycle_for_athlete(db: Session, referencia: models.Mesocycle, user_id: UUID) -> models.Mesocycle:
    """Clona la estructura completa (sesiones + series + ejercicios) de un mesociclo de grupo
    para un atleta que se acaba de unir. No copia pesos/RMs específicos de nadie más:
    copia exactamente lo que el coach ya programó (mismos ejercicios/reps/RPE/peso prescrito),
    y el coach puede ajustarlo después desde la pestaña individual del atleta."""
    nuevo_meso = models.Mesocycle(
        user_id=user_id,
        group_id=referencia.group_id,
        name=referencia.name,
        discipline=referencia.discipline,
        start_date=referencia.start_date,
        end_date=referencia.end_date,
        is_active=referencia.is_active,
    )
    db.add(nuevo_meso)
    db.flush()

    sesiones_ref = (
        db.query(models.Session)
        .options(joinedload(models.Session.sets))
        .filter(models.Session.mesocycle_id == referencia.id)
        .all()
    )
    for sesion_ref in sesiones_ref:
        nueva_sesion = models.Session(
            mesocycle_id=nuevo_meso.id,
            scheduled_date=sesion_ref.scheduled_date,
            status=sesion_ref.status,
            athlete_notes=sesion_ref.athlete_notes,
        )
        db.add(nueva_sesion)
        db.flush()
        for set_ref in sesion_ref.sets:
            db.add(models.Set(
                session_id=nueva_sesion.id,
                exercise_id=set_ref.exercise_id,
                set_order=set_ref.set_order,
                block=set_ref.block,
                prescribed_reps=set_ref.prescribed_reps,
                prescribed_weight=set_ref.prescribed_weight,
                prescribed_percentage=set_ref.prescribed_percentage,
                reference_exercise=set_ref.reference_exercise,
                rpe=set_ref.rpe,
            ))

    return nuevo_meso


@app.post("/groups/{group_id}/members", response_model=schemas.GroupResponse)
def add_group_members(
    group_id: UUID,
    req: schemas.GroupMemberAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Añade atletas al grupo y, a cada uno que sea realmente nuevo, le clona el/los
    mesociclo(s) activo(s) del grupo (mismos ejercicios/reps/RPE/peso ya programados),
    para que aparezca de inmediato en su propia pestaña de edición."""
    grupo = _get_owned_group(db, group_id, current_user)
    existentes = {m.id for m in grupo.members}
    nuevos = db.query(models.User).filter(
        models.User.id.in_(req.athlete_ids), models.User.role == "athlete"
    ).all()
    atletas_nuevos = [a for a in nuevos if a.id not in existentes]

    for atleta in atletas_nuevos:
        grupo.members.append(atleta)
    db.flush()

    # Un mesociclo de referencia por cada programa activo del grupo (mismo name + start_date)
    mesos_grupo = db.query(models.Mesocycle).filter(
        models.Mesocycle.group_id == group_id, models.Mesocycle.is_active == True
    ).all()
    programas_ref: dict[tuple, models.Mesocycle] = {}
    for m in mesos_grupo:
        clave = (m.name, m.start_date)
        programas_ref.setdefault(clave, m)

    for atleta in atletas_nuevos:
        programas_que_ya_tiene = {
            (m.name, m.start_date)
            for m in db.query(models.Mesocycle).filter(
                models.Mesocycle.user_id == atleta.id, models.Mesocycle.group_id == group_id
            ).all()
        }
        for clave, referencia in programas_ref.items():
            if clave not in programas_que_ya_tiene:
                _clone_mesocycle_for_athlete(db, referencia, atleta.id)

    db.commit()
    db.refresh(grupo)
    return grupo


@app.delete("/groups/{group_id}/members/{user_id}", response_model=schemas.GroupResponse)
def remove_group_member(
    group_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    grupo = _get_owned_group(db, group_id, current_user)
    grupo.members = [m for m in grupo.members if m.id != user_id]
    db.commit()
    db.refresh(grupo)
    return grupo


@app.delete("/groups/{group_id}")
def delete_group(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    grupo = _get_owned_group(db, group_id, current_user)
    db.delete(grupo)
    db.commit()
    return {"message": "Grupo eliminado correctamente"}


@app.get("/groups/{group_id}/mesocycles", response_model=List[schemas.GroupMesocycleProgram])
def list_group_mesocycles(
    group_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Mesociclos programados para este grupo, agrupados por programa (mismo nombre + fecha de inicio),
    cada uno con la instancia por-atleta correspondiente (una fila real de Mesocycle por atleta)."""
    _get_owned_group(db, group_id, current_user)  # valida existencia + pertenencia

    mesos = (
        db.query(models.Mesocycle)
        .options(joinedload(models.Mesocycle.user))
        .filter(models.Mesocycle.group_id == group_id)
        .order_by(models.Mesocycle.created_at.desc())
        .all()
    )

    programas: dict[tuple, schemas.GroupMesocycleProgram] = {}
    for meso in mesos:
        clave = (meso.name, meso.start_date)
        if clave not in programas:
            # Calendario compartido: cualquier atleta del programa sirve de referencia,
            # todos entrenan las mismas fechas (misma construcción del grupo).
            fechas = (
                db.query(models.Session.scheduled_date)
                .filter(models.Session.mesocycle_id == meso.id)
                .order_by(models.Session.scheduled_date)
                .all()
            )
            programas[clave] = schemas.GroupMesocycleProgram(
                name=meso.name,
                discipline=meso.discipline,
                start_date=meso.start_date,
                end_date=meso.end_date,
                created_at=meso.created_at,
                athletes=[],
                session_dates=[f[0] for f in fechas],
            )
        programas[clave].athletes.append(
            schemas.GroupMesocycleAthlete(
                user_id=meso.user_id,
                full_name=meso.user.full_name,
                mesocycle_id=meso.id,
                is_active=meso.is_active,
            )
        )

    return list(programas.values())


def _get_group_program_mesocycles(
    db: Session, group_id: UUID, program_name: str, program_start_date, current_user: models.User
) -> List[models.Mesocycle]:
    _get_owned_group(db, group_id, current_user)
    mesos = (
        db.query(models.Mesocycle)
        .options(joinedload(models.Mesocycle.user))
        .filter(
            models.Mesocycle.group_id == group_id,
            models.Mesocycle.name == program_name,
            models.Mesocycle.start_date == program_start_date,
        )
        .all()
    )
    if not mesos:
        raise HTTPException(status_code=404, detail="No se encontró ese programa para el grupo")
    return mesos


def _get_or_create_exercise(db: Session, name: str) -> models.Exercise:
    ejercicio = db.query(models.Exercise).filter(models.Exercise.name == name).first()
    if not ejercicio:
        ejercicio = models.Exercise(name=name, category="Custom")
        db.add(ejercicio)
        db.flush()
    return ejercicio


def _format_wod_summary(sesion: "models.Session | None") -> str | None:
    """Texto corto y legible del resultado de un WOD, según su formato — para la tabla de
    posiciones del coach (el detalle completo vive en /users/{id}/recent-activity)."""
    if sesion is None or not sesion.wod_format:
        return None
    if sesion.wod_format == "for_time" and sesion.wod_time_seconds is not None:
        minutos, segundos = divmod(sesion.wod_time_seconds, 60)
        return f"Por tiempo: {minutos}:{segundos:02d}"
    if sesion.wod_format == "amrap" and (sesion.wod_rounds is not None or sesion.wod_extra_reps is not None):
        rondas = sesion.wod_rounds or 0
        reps = sesion.wod_extra_reps or 0
        return f"AMRAP: {rondas} rondas + {reps} reps" if reps else f"AMRAP: {rondas} rondas"
    if sesion.wod_format == "emom" and sesion.wod_emom_completed is not None:
        return "EMOM: cumplido ✓" if sesion.wod_emom_completed else "EMOM: no completo ✗"
    if sesion.wod_format == "1rm":
        pesos = [s.actual_weight for s in sesion.sets if s.actual_weight]
        if pesos:
            return f"1RM: {max(pesos):g} kg"
    return None


_BLOQUES_VALIDOS = {"warmup", "strength", "weightlifting", "skills", "metcon", "accessory", "main"}


def _clean_ai_block(value) -> str | None:
    """Normaliza el bloque que devuelve la IA: minúsculas, recortado, y descartado si no es uno
    de los valores válidos (ver schemas.Bloque) — mejor guardar None que un string inventado."""
    if not isinstance(value, str):
        return None
    limpio = value.strip().lower()
    return limpio if limpio in _BLOQUES_VALIDOS else None


@app.post("/groups/{group_id}/sessions/bulk-add-exercise")
def add_exercise_to_group_session(
    group_id: UUID,
    req: schemas.GroupSessionExerciseAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Añade el mismo ejercicio (mismas series/reps/RPE/peso) a la sesión de una fecha dada,
    para TODOS los atletas del programa a la vez. Útil para ajustes que aplican a todo el equipo."""
    mesos = _get_group_program_mesocycles(db, group_id, req.program_name, req.program_start_date, current_user)
    ejercicio = _get_or_create_exercise(db, req.exercise_name)

    resultados = []
    for meso in mesos:
        sesion = db.query(models.Session).filter(
            models.Session.mesocycle_id == meso.id,
            models.Session.scheduled_date == req.scheduled_date,
        ).first()

        if not sesion:
            resultados.append({"full_name": meso.user.full_name, "status": "sin sesión en esa fecha"})
            continue

        series_actuales = db.query(models.Set).filter(models.Set.session_id == sesion.id).count()
        for i in range(req.prescribed_sets):
            db.add(models.Set(
                session_id=sesion.id,
                exercise_id=ejercicio.id,
                set_order=series_actuales + i + 1,
                prescribed_reps=req.prescribed_reps,
                rpe=req.rpe,
                prescribed_weight=req.prescribed_weight,
                block=req.block,
            ))
        resultados.append({"full_name": meso.user.full_name, "status": "añadido"})

    db.commit()
    exitosos = sum(1 for r in resultados if r["status"] == "añadido")
    return {
        "message": f"'{req.exercise_name}' añadido a {exitosos}/{len(resultados)} atleta(s) del grupo para el {req.scheduled_date}",
        "results": resultados,
    }


@app.put("/groups/{group_id}/sessions/bulk-update-exercise")
def update_exercise_in_group_session(
    group_id: UUID,
    req: schemas.GroupSessionExerciseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Edita (nombre/series/reps/RPE/peso) un ejercicio ya existente en la sesión de una fecha dada,
    para TODOS los atletas del programa. Cada atleta conserva su propio peso salvo que el coach
    lo cambie explícitamente aquí (en cuyo caso se aplica el mismo peso a todos)."""
    mesos = _get_group_program_mesocycles(db, group_id, req.program_name, req.program_start_date, current_user)
    nuevo_ejercicio = _get_or_create_exercise(db, req.new_exercise_name)

    resultados = []
    for meso in mesos:
        sesion = db.query(models.Session).filter(
            models.Session.mesocycle_id == meso.id,
            models.Session.scheduled_date == req.scheduled_date,
        ).first()
        if not sesion:
            resultados.append({"full_name": meso.user.full_name, "status": "sin sesión en esa fecha"})
            continue

        sets_existentes = (
            db.query(models.Set)
            .join(models.Exercise, models.Set.exercise_id == models.Exercise.id)
            .filter(models.Set.session_id == sesion.id, models.Exercise.name == req.exercise_name)
            .order_by(models.Set.set_order)
            .all()
        )
        if not sets_existentes:
            resultados.append({"full_name": meso.user.full_name, "status": "no tenía ese ejercicio en esa fecha"})
            continue

        num_original = len(sets_existentes)
        limite = min(num_original, req.prescribed_sets)
        for i in range(limite):
            sets_existentes[i].exercise_id = nuevo_ejercicio.id
            sets_existentes[i].prescribed_reps = req.prescribed_reps
            sets_existentes[i].rpe = req.rpe
            sets_existentes[i].prescribed_weight = req.prescribed_weight
            if req.block is not None:
                sets_existentes[i].block = req.block

        if req.prescribed_sets < num_original:
            for extra in sets_existentes[req.prescribed_sets:]:
                db.delete(extra)
        elif req.prescribed_sets > num_original:
            bloque_nuevas = req.block if req.block is not None else sets_existentes[0].block
            for i in range(num_original, req.prescribed_sets):
                db.add(models.Set(
                    session_id=sesion.id,
                    exercise_id=nuevo_ejercicio.id,
                    set_order=i + 1,
                    prescribed_reps=req.prescribed_reps,
                    rpe=req.rpe,
                    prescribed_weight=req.prescribed_weight,
                    block=bloque_nuevas,
                ))

        resultados.append({"full_name": meso.user.full_name, "status": "actualizado"})

    db.commit()
    exitosos = sum(1 for r in resultados if r["status"] == "actualizado")
    return {
        "message": f"'{req.exercise_name}' actualizado en {exitosos}/{len(resultados)} atleta(s) del grupo",
        "results": resultados,
    }


@app.post("/groups/{group_id}/sessions/bulk-delete-exercise")
def delete_exercise_from_group_session(
    group_id: UUID,
    req: schemas.GroupSessionExerciseDelete,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Elimina por completo un ejercicio (todas sus series) de la sesión de una fecha dada,
    para TODOS los atletas del programa."""
    mesos = _get_group_program_mesocycles(db, group_id, req.program_name, req.program_start_date, current_user)

    resultados = []
    for meso in mesos:
        sesion = db.query(models.Session).filter(
            models.Session.mesocycle_id == meso.id,
            models.Session.scheduled_date == req.scheduled_date,
        ).first()
        if not sesion:
            resultados.append({"full_name": meso.user.full_name, "status": "sin sesión en esa fecha"})
            continue

        sets_existentes = (
            db.query(models.Set)
            .join(models.Exercise, models.Set.exercise_id == models.Exercise.id)
            .filter(models.Set.session_id == sesion.id, models.Exercise.name == req.exercise_name)
            .all()
        )
        for s in sets_existentes:
            db.delete(s)
        resultados.append({"full_name": meso.user.full_name, "status": "eliminado" if sets_existentes else "no tenía ese ejercicio"})

    db.commit()
    exitosos = sum(1 for r in resultados if r["status"] == "eliminado")
    return {
        "message": f"'{req.exercise_name}' eliminado de {exitosos}/{len(resultados)} atleta(s) del grupo",
        "results": resultados,
    }


# --- ENDPOINTS PARA MESOCICLOS (solo coach: crear/editar rutinas de atletas) ---

@app.post("/mesocycles/", response_model=schemas.MesocycleResponse)
def create_mesocycle(
    mesocycle: schemas.MesocycleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    db_user = db.query(models.User).filter(models.User.id == mesocycle.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    ensure_owner_or_coach(db, db_user.id, current_user)

    new_meso = models.Mesocycle(
        user_id=mesocycle.user_id,
        name=mesocycle.name,
        discipline=mesocycle.discipline,
        start_date=mesocycle.start_date,
    )
    db.add(new_meso)
    db.commit()
    db.refresh(new_meso)
    return new_meso


@app.get("/mesocycles/", response_model=List[schemas.MesocycleResponse])
def listar_mesociclos(db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    """Mesociclos básicos (sin plantillas de planes). Un admin los ve todos; un coach, solo los
    de sus propios atletas."""
    query = db.query(models.Mesocycle).filter(models.Mesocycle.is_template == False)
    if current_user.role != "admin":
        ids = _coach_athlete_ids(db, current_user.id)
        if not ids:
            return []
        query = query.filter(models.Mesocycle.user_id.in_(ids))
    return query.all()


@app.get("/mesocycles/{mesocycle_id}", response_model=schemas.MesocycleFullResponse)
def get_full_mesocycle(
    mesocycle_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Obtiene un mesociclo completo con todas sus sesiones, series y ejercicios anidados."""
    meso = db.query(models.Mesocycle).options(
        joinedload(models.Mesocycle.sessions)
        .joinedload(models.Session.sets)
        .joinedload(models.Set.exercise)
    ).filter(models.Mesocycle.id == mesocycle_id).first()

    if not meso:
        raise HTTPException(status_code=404, detail="Mesociclo no encontrado")

    ensure_owner_or_coach(db, meso.user_id, current_user)

    # Ordenamos sesiones por fecha y series por su set_order
    meso.sessions.sort(key=lambda s: s.scheduled_date)
    for sesion in meso.sessions:
        sesion.sets.sort(key=lambda serie: serie.set_order)

    return meso


def _build_manual_mesocycle(
    db: Session,
    user_id: UUID,
    name: str,
    discipline: str,
    start_date,
    weeks_count: int,
    training_days: List[int],
    group_id: UUID | None = None,
) -> dict:
    """Crea el cascarón de un mesociclo manual y sus sesiones vacías para UN atleta. Hace commit propio."""
    nuevo_meso = models.Mesocycle(
        user_id=user_id,
        group_id=group_id,
        name=name,
        discipline=discipline,
        start_date=start_date,
    )
    db.add(nuevo_meso)
    db.flush()

    total_dias_mesociclo = weeks_count * 7
    sesiones_creadas = 0

    for i in range(total_dias_mesociclo):
        fecha_evaluada = start_date + timedelta(days=i)
        if fecha_evaluada.weekday() in training_days:
            nueva_sesion = models.Session(
                mesocycle_id=nuevo_meso.id,
                scheduled_date=fecha_evaluada,
                athlete_notes="Sesión manual. Añade tus ejercicios.",
                status="pending",
            )
            db.add(nueva_sesion)
            sesiones_creadas += 1

    nuevo_meso.end_date = start_date + timedelta(days=total_dias_mesociclo - 1)
    db.commit()

    return {"mesocycle_id": str(nuevo_meso.id), "total_sessions": sesiones_creadas}


@app.post("/mesocycles/manual")
def create_manual_mesocycle(
    req: schemas.MesocycleManualCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Crea el cascarón del mesociclo y las sesiones vacías según el calendario."""
    db_user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    ensure_owner_or_coach(db, db_user.id, current_user)

    resultado = _build_manual_mesocycle(
        db, req.user_id, req.name, req.discipline, req.start_date, req.weeks_count, req.training_days
    )
    return {"message": "Mesociclo manual creado con éxito", **resultado}


@app.post("/mesocycles/manual/group")
def create_manual_mesocycle_for_group(
    req: schemas.MesocycleManualGroupCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Crea el mismo mesociclo manual (cascarón + calendario) para cada atleta del grupo."""
    grupo = _get_owned_group(db, req.group_id, current_user)
    if not grupo.members:
        raise HTTPException(status_code=400, detail="El grupo no tiene atletas asignados")

    resultados = []
    for atleta in grupo.members:
        resultado = _build_manual_mesocycle(
            db, atleta.id, req.name, req.discipline, req.start_date, req.weeks_count, req.training_days,
            group_id=grupo.id,
        )
        resultados.append({"user_id": str(atleta.id), "full_name": atleta.full_name, **resultado})

    return {
        "message": f"Mesociclo manual creado para {len(resultados)} atleta(s) del grupo '{grupo.name}'",
        "results": resultados,
    }


# --- ENDPOINTS PARA SESIONES ---

@app.post("/sessions/", response_model=schemas.SessionResponse)
def create_session(
    session: schemas.SessionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    db_meso = db.query(models.Mesocycle).filter(models.Mesocycle.id == session.mesocycle_id).first()
    if not db_meso:
        raise HTTPException(status_code=404, detail="Mesociclo no encontrado")
    ensure_owner_or_coach(db, db_meso.user_id, current_user)

    new_session = models.Session(
        mesocycle_id=session.mesocycle_id,
        scheduled_date=session.scheduled_date,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


# --- ENDPOINTS PARA SERIES (SETS) ---

@app.put("/sets/{set_id}", response_model=schemas.SetResponse)
def update_set(
    set_id: UUID,
    set_update: schemas.SetUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    db_set = (
        db.query(models.Set)
        .options(joinedload(models.Set.session).joinedload(models.Session.mesocycle))
        .filter(models.Set.id == set_id)
        .first()
    )
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie (Set) no encontrada")
    ensure_owner_or_coach(db, db_set.session.mesocycle.user_id, current_user)

    db_set.prescribed_reps = set_update.prescribed_reps
    db_set.rpe = set_update.rpe
    db_set.prescribed_weight = set_update.prescribed_weight
    if set_update.block is not None:
        db_set.block = set_update.block

    if set_update.exercise_name:
        ejercicio = db.query(models.Exercise).filter(models.Exercise.name == set_update.exercise_name).first()
        if not ejercicio:
            ejercicio = models.Exercise(name=set_update.exercise_name, category="General")
            db.add(ejercicio)
            db.flush()
        db_set.exercise_id = ejercicio.id

    db.commit()
    db.refresh(db_set)
    return db_set


@app.post("/sessions/{session_id}/sets/")
def agregar_serie(
    session_id: UUID,
    req: schemas.SetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    sesion = (
        db.query(models.Session)
        .options(joinedload(models.Session.mesocycle))
        .filter(models.Session.id == session_id)
        .first()
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    ensure_owner_or_coach(db, sesion.mesocycle.user_id, current_user)

    ejercicio = db.query(models.Exercise).filter(models.Exercise.name == req.exercise_name).first()
    if not ejercicio:
        ejercicio = models.Exercise(name=req.exercise_name, category="Custom")
        db.add(ejercicio)
        db.flush()

    series_actuales = db.query(models.Set).filter(models.Set.session_id == session_id).all()
    siguiente_orden = len(series_actuales) + 1

    nuevo_set = models.Set(
        session_id=session_id,
        exercise_id=ejercicio.id,
        set_order=siguiente_orden,
        prescribed_reps=req.prescribed_reps,
        rpe=req.rpe,
        prescribed_weight=req.prescribed_weight,
        block=req.block,
    )
    db.add(nuevo_set)
    db.commit()
    return {"message": "Nueva serie agregada al final de la sesión"}


@app.delete("/sets/{set_id}")
def delete_set(set_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    db_set = (
        db.query(models.Set)
        .options(joinedload(models.Set.session).joinedload(models.Session.mesocycle))
        .filter(models.Set.id == set_id)
        .first()
    )
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    ensure_owner_or_coach(db, db_set.session.mesocycle.user_id, current_user)

    db.delete(db_set)
    db.commit()
    return {"message": "Serie eliminada correctamente"}


@app.put("/sets/{set_id}/log", response_model=schemas.SetResponse)
def log_set_performance(
    set_id: UUID,
    log: schemas.SetLogUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """El ATLETA (dueño) o su coach registran lo que realmente se hizo en una serie
    (reps/peso reales, feedback de técnica) — a diferencia de PUT /sets/{id}, que edita
    lo PRESCRITO y es solo para coaches."""
    db_set = (
        db.query(models.Set)
        .options(joinedload(models.Set.session).joinedload(models.Session.mesocycle))
        .filter(models.Set.id == set_id)
        .first()
    )
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie no encontrada")

    ensure_owner_or_coach(db, db_set.session.mesocycle.user_id, current_user)

    db_set.actual_reps = log.actual_reps
    db_set.actual_weight = log.actual_weight
    if log.technique_feedback is not None:
        db_set.technique_feedback = log.technique_feedback

    db.commit()
    db.refresh(db_set)
    return db_set


@app.put("/sessions/{session_id}/wod-format", response_model=schemas.MessageResponse)
def set_session_wod_format(
    session_id: UUID,
    req: schemas.WodFormatUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """El coach marca (o quita) qué formato de WOD tiene esta sesión — así el atleta sabe qué
    reportar al completarla (tiempo, rondas+reps, o si cumplió el EMOM)."""
    sesion = (
        db.query(models.Session)
        .options(joinedload(models.Session.mesocycle))
        .filter(models.Session.id == session_id)
        .first()
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    ensure_owner_or_coach(db, sesion.mesocycle.user_id, current_user)

    sesion.wod_format = req.wod_format
    db.commit()
    return {"message": "Formato de WOD actualizado" if req.wod_format else "Formato de WOD quitado"}


@app.post("/sessions/{session_id}/complete")
def complete_session(
    session_id: UUID,
    req: schemas.SessionCompleteRequest | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """El ATLETA (dueño) o su coach marcan una sesión como completada. Si la sesión tenía un
    formato de WOD prescrito (wod_format), `req` trae el resultado real que reportó el atleta
    (tiempo, rondas+reps, o si cumplió el EMOM) — queda guardado junto con la sesión."""
    sesion = (
        db.query(models.Session)
        .options(joinedload(models.Session.mesocycle))
        .filter(models.Session.id == session_id)
        .first()
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    ensure_owner_or_coach(db, sesion.mesocycle.user_id, current_user)

    sesion.status = "completed"
    sesion.completed_date = datetime.utcnow()
    if req is not None:
        if req.wod_time_seconds is not None:
            sesion.wod_time_seconds = req.wod_time_seconds
        if req.wod_rounds is not None:
            sesion.wod_rounds = req.wod_rounds
        if req.wod_extra_reps is not None:
            sesion.wod_extra_reps = req.wod_extra_reps
        if req.wod_emom_completed is not None:
            sesion.wod_emom_completed = req.wod_emom_completed
    db.commit()
    return {"message": "Sesión marcada como completada"}


@app.post("/sessions/{session_id}/adapt", response_model=schemas.SessionResponse)
@limiter.limit("10/hour")
def adapt_session_to_available_time(
    request: Request,
    session_id: UUID,
    req: schemas.SessionAdaptRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """El ATLETA (dueño) o su coach piden una versión adaptada de una sesión ya prescrita para
    caber en `available_minutes` (p. ej. "hoy solo tengo 60 min"). La sesión ORIGINAL nunca se
    toca: esto crea (o actualiza, si ya se había pedido antes) una segunda sesión "hija" para
    el mismo día, que el atleta puede ver junto a la original y elegir cuál seguir."""
    original = (
        db.query(models.Session)
        .options(
            joinedload(models.Session.mesocycle).joinedload(models.Mesocycle.user),
            joinedload(models.Session.sets).joinedload(models.Set.exercise),
        )
        .filter(models.Session.id == session_id)
        .first()
    )
    if not original:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    ensure_owner_or_coach(db, original.mesocycle.user_id, current_user)

    if original.parent_session_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Esta ya es una versión adaptada; pide la adaptación desde la sesión original.",
        )

    if not original.sets:
        raise HTTPException(status_code=400, detail="Esta sesión todavía no tiene ejercicios para adaptar.")

    atleta = original.mesocycle.user
    marcas = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == atleta.id).all()
    texto_marcas = ", ".join(f"{pr.exercise_name}: {pr.max_weight_kg}kg" for pr in marcas) or "Sin marcas registradas."
    peso_corporal = f"{atleta.body_weight}kg" if atleta.body_weight else "No registrado"
    contexto = f"Peso corporal: {peso_corporal}. Marcas (1RM): {texto_marcas}."

    ejercicios_originales = [
        {
            "exercise_name": s.exercise.name,
            "prescribed_sets": 1,  # cada fila ya es una serie individual
            "prescribed_reps": s.prescribed_reps,
            "rpe": s.rpe,
            "prescribed_weight": s.prescribed_weight,
            "block": s.block,
        }
        for s in original.sets
    ]

    rutina_ai = ai_agent.adapt_session_to_time(
        athlete_name=atleta.full_name,
        discipline=original.mesocycle.discipline,
        experience_notes=contexto,
        original_exercises=ejercicios_originales,
        available_minutes=req.available_minutes,
    )
    if "error" in rutina_ai:
        raise HTTPException(status_code=500, detail=f"Error generando la sesión adaptada: {rutina_ai['error']}")

    # ¿Ya existía una versión adaptada de esta sesión? La reemplazamos en vez de duplicar.
    adaptada = db.query(models.Session).filter(models.Session.parent_session_id == original.id).first()
    if adaptada:
        db.query(models.Set).filter(models.Set.session_id == adaptada.id).delete()
    else:
        adaptada = models.Session(
            mesocycle_id=original.mesocycle_id,
            scheduled_date=original.scheduled_date,
            parent_session_id=original.id,
            status="pending",
        )
        db.add(adaptada)
        db.flush()

    adaptada.duration_minutes = req.available_minutes
    adaptada.athlete_notes = rutina_ai.get(
        "athlete_notes", f"Versión adaptada a {req.available_minutes} minutos."
    )

    orden = 1
    for ej_data in rutina_ai.get("exercises", []):
        ejercicio = _get_or_create_exercise(db, ej_data.get("exercise_name", "Ejercicio Desconocido"))
        db.add(models.Set(
            session_id=adaptada.id,
            exercise_id=ejercicio.id,
            set_order=orden,
            prescribed_reps=ej_data.get("prescribed_reps", 1),
            rpe=ej_data.get("rpe_target"),
            prescribed_weight=ej_data.get("prescribed_weight"),
            block=_clean_ai_block(ej_data.get("block")),
        ))
        orden += 1

    db.commit()
    db.refresh(adaptada)
    return adaptada


# --- ENDPOINTS DE GENERACIÓN CON IA (solo coach) ---

@app.post("/ai/generate-session/")
@limiter.limit("20/hour")
def generate_and_save_session(
    request: Request,
    req: schemas.AIGenerateRequest, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    meso = db.query(models.Mesocycle).filter(models.Mesocycle.id == req.mesocycle_id).first()
    if not meso:
        raise HTTPException(status_code=404, detail="Mesociclo no encontrado")
    ensure_owner_or_coach(db, meso.user_id, current_user)

    from backend.ai_agent import generate_workout_session
    rutina_ai = generate_workout_session(
        athlete_name=meso.user.full_name,
        discipline=meso.discipline,
        experience_notes=req.context,
    )

    if "error" in rutina_ai:
        raise HTTPException(status_code=500, detail=rutina_ai["error"])

    nueva_sesion = models.Session(
        mesocycle_id=meso.id,
        scheduled_date=date.today(),
        athlete_notes=rutina_ai.get("athlete_notes", ""),
        status="pending",
    )
    db.add(nueva_sesion)
    db.flush()

    orden = 1
    for ex_data in rutina_ai.get("exercises", []):
        ejercicio = db.query(models.Exercise).filter(models.Exercise.name == ex_data["exercise_name"]).first()
        if not ejercicio:
            ejercicio = models.Exercise(name=ex_data["exercise_name"], category="AI Generated")
            db.add(ejercicio)
            db.flush()

        nuevo_set = models.Set(
            session_id=nueva_sesion.id,
            exercise_id=ejercicio.id,
            set_order=orden,
            prescribed_reps=ex_data["prescribed_reps"],
            rpe=ex_data["rpe_target"],
            block=_clean_ai_block(ex_data.get("block")),
        )
        db.add(nuevo_set)
        orden += 1

    db.commit()
    db.refresh(nueva_sesion)

    return {"status": "success", "session_focus": rutina_ai.get("session_focus"), "session_id": nueva_sesion.id}


def _build_smart_mesocycle(
    db: Session,
    atleta: models.User,
    name: str,
    discipline: str,
    start_date,
    weeks_count: int,
    training_days: List[int],
    context: str,
    group_id: UUID | None = None,
    session_duration_minutes: int | None = None,
) -> dict:
    """Genera con IA un mesociclo inteligente completo para UN atleta. Hace commit propio;
    en caso de error hace rollback y relanza la excepción (el llamador decide cómo manejarla)."""
    # 1. Crear el cascarón del mesociclo
    nuevo_meso = models.Mesocycle(
        user_id=atleta.id,
        group_id=group_id,
        name=name,
        discipline=discipline,
        start_date=start_date,
    )
    db.add(nuevo_meso)
    db.flush()

    # 2. Construir el súper contexto (peso y RMs)
    marcas = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == atleta.id).all()

    texto_marcas = "Sin marcas registradas."
    if marcas:
        texto_marcas = ", ".join([f"{pr.exercise_name}: {pr.max_weight_kg}kg" for pr in marcas])

    peso_corporal = f"{atleta.body_weight}kg" if atleta.body_weight else "No registrado"
    contexto_enriquecido = f"Peso corporal: {peso_corporal}. Marcas (1RM): {texto_marcas}. Peticiones: {context}"

    # 3. Calcular todas las fechas del mesociclo
    total_dias = weeks_count * 7
    todas_las_fechas = []
    for i in range(total_dias):
        fecha_evaluada = start_date + timedelta(days=i)
        if fecha_evaluada.weekday() in training_days:
            todas_las_fechas.append(fecha_evaluada.strftime("%Y-%m-%d"))

    semanas_por_chunk = 2
    sesiones_por_semana = len(training_days)
    sesiones_por_chunk = semanas_por_chunk * sesiones_por_semana

    try:
        # 4. Bucle de generación por "chunks" (semanas)
        from backend.ai_agent import generate_mesocycle_chunk

        for start in range(1, weeks_count + 1, semanas_por_chunk):
            end = min(start + semanas_por_chunk - 1, weeks_count)

            idx_inicio = (start - 1) * sesiones_por_semana
            idx_fin = idx_inicio + sesiones_por_chunk
            fechas_del_chunk = todas_las_fechas[idx_inicio:idx_fin]

            rutina_ai = generate_mesocycle_chunk(
                athlete_name=atleta.full_name,
                discipline=discipline,
                experience_notes=contexto_enriquecido,
                start_week=start,
                end_week=end,
                session_dates=fechas_del_chunk,
                session_duration_minutes=session_duration_minutes,
            )

            # 5. Parseo y guardado en base de datos
            semanas = rutina_ai.get("weeks", [])
            for semana in semanas:
                sesiones = semana.get("sessions", [])

                for sesion_data in sesiones:
                    fecha_str = sesion_data.get("scheduled_date")
                    if fecha_str:
                        fecha_real = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    else:
                        fecha_real = start_date  # Fallback por seguridad

                    nueva_sesion = models.Session(
                        mesocycle_id=nuevo_meso.id,
                        scheduled_date=fecha_real,
                        athlete_notes=sesion_data.get("athlete_notes", ""),
                        status="pending",
                        duration_minutes=session_duration_minutes,
                    )
                    db.add(nueva_sesion)
                    db.flush()

                    contador_orden = 1
                    ejercicios = sesion_data.get("exercises", [])

                    for ej_data in ejercicios:
                        nombre_ejercicio = ej_data.get("exercise_name", "Ejercicio Desconocido")
                        ejercicio = db.query(models.Exercise).filter(models.Exercise.name == nombre_ejercicio).first()
                        if not ejercicio:
                            ejercicio = models.Exercise(name=nombre_ejercicio, category="General")
                            db.add(ejercicio)
                            db.flush()

                        num_series = ej_data.get("prescribed_sets", 1)
                        reps = ej_data.get("prescribed_reps", 1)

                        rpe_raw = ej_data.get("rpe_target") or ej_data.get("rpe")
                        rpe_limpio = int(float(rpe_raw)) if rpe_raw is not None else None

                        peso_raw = (
                            ej_data.get("prescribed_weight")
                            or ej_data.get("weight_kg")
                            or ej_data.get("weight")
                            or ej_data.get("target_weight")
                        )
                        peso_limpio = None
                        if peso_raw is not None:
                            try:
                                peso_limpio = float(peso_raw)
                            except (ValueError, TypeError):
                                peso_limpio = None

                        bloque_limpio = _clean_ai_block(ej_data.get("block"))

                        for _ in range(num_series):
                            nuevo_set = models.Set(
                                session_id=nueva_sesion.id,
                                exercise_id=ejercicio.id,
                                set_order=contador_orden,
                                prescribed_reps=reps,
                                rpe=rpe_limpio,
                                prescribed_weight=peso_limpio,
                                block=bloque_limpio,
                            )
                            db.add(nuevo_set)
                            contador_orden += 1

        # 6. Actualizar la fecha de fin
        nuevo_meso.end_date = datetime.strptime(todas_las_fechas[-1], "%Y-%m-%d").date()
        db.commit()
        return {"mesocycle_id": str(nuevo_meso.id)}

    except Exception as e:
        db.rollback()
        raise RuntimeError(str(e)) from e


MAX_ATLETAS_POR_GENERACION_GRUPAL = 25  # cada atleta dispara su propia tanda de llamadas a Gemini


@app.post("/ai/generate-smart-mesocycle/")
@limiter.limit("10/hour")
def generate_and_save_smart_mesocycle(
    request: Request,
    req: schemas.AIGenerateSmart, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    atleta = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not atleta:
        raise HTTPException(status_code=404, detail="Atleta no encontrado")
    ensure_owner_or_coach(db, atleta.id, current_user)

    try:
        _build_smart_mesocycle(
            db, atleta, req.name, req.discipline, req.start_date, req.weeks_count, req.training_days, req.context,
            session_duration_minutes=req.session_duration_minutes,
        )
        return {"message": "Mesociclo Inteligente generado y guardado exitosamente."}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Error interno generando la rutina: {str(e)}")


@app.post("/ai/generate-smart-mesocycle/group")
@limiter.limit("3/hour")
def generate_and_save_smart_mesocycle_for_group(
    request: Request,
    req: schemas.AIGenerateSmartGroup, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Genera con IA el mismo mesociclo (contexto compartido + marcas propias de cada atleta) para todo el grupo.
    Se ejecuta atleta por atleta y cada uno hace su propio commit, así que si uno falla
    (p. ej. error de la IA) no se pierde el trabajo ya guardado de los demás."""
    grupo = _get_owned_group(db, req.group_id, current_user)
    if not grupo.members:
        raise HTTPException(status_code=400, detail="El grupo no tiene atletas asignados")
    if len(grupo.members) > MAX_ATLETAS_POR_GENERACION_GRUPAL:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Este grupo tiene {len(grupo.members)} atletas; el máximo para generar con IA de una vez "
                f"es {MAX_ATLETAS_POR_GENERACION_GRUPAL} (cada atleta dispara varias llamadas a Gemini). "
                "Divide el grupo en subgrupos más pequeños."
            ),
        )

    resultados = []
    for atleta in grupo.members:
        try:
            resultado = _build_smart_mesocycle(
                db, atleta, req.name, req.discipline, req.start_date, req.weeks_count, req.training_days, req.context,
                group_id=grupo.id, session_duration_minutes=req.session_duration_minutes,
            )
            resultados.append({"user_id": str(atleta.id), "full_name": atleta.full_name, "status": "success", **resultado})
        except RuntimeError as e:
            resultados.append({"user_id": str(atleta.id), "full_name": atleta.full_name, "status": "error", "detail": str(e)})

    exitosos = sum(1 for r in resultados if r["status"] == "success")
    return {
        "message": f"Mesociclo generado para {exitosos}/{len(resultados)} atleta(s) del grupo '{grupo.name}'",
        "results": resultados,
    }


# ==========================================
# PANEL DE ADMINISTRACIÓN (solo rol 'admin')
# ==========================================

@app.get("/admin/overview", response_model=schemas.AdminOverview)
def get_admin_overview(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Vista completa de la app: conteos globales sin importar de qué coach o atleta sean."""
    total_users = db.query(models.User).count()
    total_coaches = db.query(models.User).filter(models.User.role == "coach").count()
    total_athletes = db.query(models.User).filter(models.User.role == "athlete").count()
    total_admins = db.query(models.User).filter(models.User.role == "admin").count()
    total_groups = db.query(models.Group).count()
    total_mesocycles = db.query(models.Mesocycle).filter(models.Mesocycle.is_template == False).count()
    total_sessions = db.query(models.Session).count()
    sessions_completed = db.query(models.Session).filter(models.Session.status == "completed").count()

    return schemas.AdminOverview(
        total_users=total_users,
        total_coaches=total_coaches,
        total_athletes=total_athletes,
        total_admins=total_admins,
        total_groups=total_groups,
        total_mesocycles=total_mesocycles,
        total_sessions=total_sessions,
        sessions_completed=sessions_completed,
        sessions_pending=total_sessions - sessions_completed,
    )


@app.put("/admin/users/{user_id}/role", response_model=schemas.UserResponse)
def update_user_role(
    user_id: UUID,
    req: schemas.UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Cambia el rol de cualquier usuario (promover a coach/admin, o degradar a atleta)."""
    if user_id == current_user.id and req.role != "admin":
        raise HTTPException(status_code=400, detail="No puedes quitarte a ti mismo el rol de admin")

    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    rol_anterior = usuario.role
    usuario.role = req.role
    db.commit()
    db.refresh(usuario)

    security_logger.info(
        "Cambio de rol: admin=%s cambió a usuario=%s de rol '%s' a '%s'",
        current_user.email, usuario.email, rol_anterior, req.role,
    )
    return usuario


@app.post("/admin/users/{user_id}/revoke-sessions", response_model=schemas.MessageResponse)
def revoke_user_sessions(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Fuerza la revocación de TODOS los tokens de un usuario (todos sus dispositivos),
    útil ante sospecha de cuenta comprometida — sin esperar a que el token expire por sí solo."""
    usuario = db.query(models.User).filter(models.User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.token_version += 1
    db.commit()

    security_logger.warning(
        "Revocación forzada: admin=%s revocó todas las sesiones de usuario=%s",
        current_user.email, usuario.email,
    )
    return {"message": f"Todas las sesiones de {usuario.full_name} fueron revocadas."}


# ==========================================
# PLANES (plantillas vendibles, sin dueño)
# ==========================================
# Un plan es un Mesocycle con is_template=True y user_id=None. Sus sesiones guardan el "día N"
# relativo (day_offset) más una fecha sintética (PLAN_EPOCH + day_offset) para no romper el
# ordenamiento ni las vistas que asumen que scheduled_date existe. Al adquirirlo, se clona a un
# mesociclo normal con las fechas reales del atleta y las cargas resueltas desde sus propias marcas.
PLAN_EPOCH = date(2000, 1, 1)


def _get_owned_plan(db: Session, plan_id: UUID, current_user: models.User) -> models.Mesocycle:
    plan = db.query(models.Mesocycle).filter(
        models.Mesocycle.id == plan_id, models.Mesocycle.is_template == True
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if current_user.role != "admin" and plan.created_by_coach_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este plan no te pertenece")
    return plan


def _plan_summary(db: Session, plan: models.Mesocycle) -> schemas.PlanSummaryResponse:
    sesiones = db.query(models.Session).filter(models.Session.mesocycle_id == plan.id).all()
    dias_distintos = {s.day_offset for s in sesiones if s.day_offset is not None}
    semanas = max(1, ((max(dias_distintos) // 7) + 1) if dias_distintos else 1)
    return schemas.PlanSummaryResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        discipline=plan.discipline,
        level=plan.level,
        price=plan.price,
        weeks_count=semanas,
        sessions_count=len(sesiones),
        sessions_per_week=round(len(sesiones) / semanas) if semanas else len(sesiones),
        coach_name=plan.created_by_coach.full_name if plan.created_by_coach else None,
        is_published=plan.is_published,
        has_cover_image=plan.has_cover_image,
        created_at=plan.created_at,
    )


@app.post("/plans/", response_model=schemas.PlanSummaryResponse)
def create_plan(
    req: schemas.PlanCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    """Crea el esqueleto de un plan: la plantilla y sus días vacíos, listos para que el coach
    les agregue ejercicios. No pertenece a ningún atleta y nace despublicado (borrador)."""
    plan = models.Mesocycle(
        user_id=None,
        is_template=True,
        is_published=False,
        created_by_coach_id=current_user.id,
        name=req.name,
        description=req.description,
        discipline=req.discipline,
        level=req.level,
        price=req.price,
        start_date=PLAN_EPOCH,
    )
    db.add(plan)
    db.flush()

    # Los offsets se normalizan para que el PRIMER día de entrenamiento sea el día 0. Así, al
    # adquirir el plan, la primera sesión cae exactamente en la fecha que eligió el atleta y el
    # patrón semanal del coach (ej. lun/mié/vie -> +0/+2/+4) se conserva tal cual, sin importar
    # en qué día de la semana empiece cada comprador.
    offsets_crudos = [
        i for i in range(req.weeks_count * 7)
        if (PLAN_EPOCH + timedelta(days=i)).weekday() in req.training_days
    ]
    base = offsets_crudos[0] if offsets_crudos else 0
    offsets = [i - base for i in offsets_crudos]

    for offset in offsets:
        db.add(models.Session(
            mesocycle_id=plan.id,
            day_offset=offset,
            scheduled_date=PLAN_EPOCH + timedelta(days=offset),
            athlete_notes="",
            status="pending",
        ))

    plan.end_date = PLAN_EPOCH + timedelta(days=max(offsets) if offsets else 0)
    db.commit()
    db.refresh(plan)
    return _plan_summary(db, plan)


@app.post("/plans/{plan_id}/cover", response_model=schemas.PlanSummaryResponse)
@limiter.limit("10/hour", key_func=_ip_and_user_key)
async def upload_plan_cover(
    request: Request,
    plan_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Sube (o reemplaza) la foto de portada del plan — mismo pipeline de saneo que el avatar
    de usuario (magic-number, re-render sin metadatos, nombre aleatorio)."""
    plan = _get_owned_plan(db, plan_id, current_user)
    raw = await avatars.read_and_validate_upload(file)
    clean_bytes, extension = avatars.rerender_and_strip_metadata(raw)

    nombre_anterior = plan.cover_image_filename
    nuevo_nombre = storage.upload_object(
        storage.PLAN_COVER_BUCKET, clean_bytes, extension, _AVATAR_CONTENT_TYPES[extension]
    )
    plan.cover_image_filename = nuevo_nombre
    db.commit()
    db.refresh(plan)
    storage.delete_object(storage.PLAN_COVER_BUCKET, nombre_anterior)
    return _plan_summary(db, plan)


@app.delete("/plans/{plan_id}/cover", response_model=schemas.MessageResponse)
def delete_plan_cover(
    plan_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)
):
    plan = _get_owned_plan(db, plan_id, current_user)
    if not plan.cover_image_filename:
        raise HTTPException(status_code=404, detail="Este plan no tiene foto de portada.")
    storage.delete_object(storage.PLAN_COVER_BUCKET, plan.cover_image_filename)
    plan.cover_image_filename = None
    db.commit()
    return {"message": "Foto de portada eliminada."}


@app.get("/plans/{plan_id}/cover")
def get_plan_cover(
    plan_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Mismo criterio de visibilidad que GET /plans/{id}: el autor/admin ve la portada de
    borradores, cualquiera autenticado ve la de planes ya publicados."""
    plan = db.query(models.Mesocycle).filter(
        models.Mesocycle.id == plan_id, models.Mesocycle.is_template == True
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    es_autor = plan.created_by_coach_id == current_user.id or current_user.role == "admin"
    if not plan.is_published and not es_autor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este plan todavía no está publicado")
    return _redirect_to_image(storage.PLAN_COVER_BUCKET, plan.cover_image_filename)


@app.get("/plans/mine", response_model=List[schemas.PlanSummaryResponse])
def list_my_plans(db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    """Planes creados por este coach (publicados y borradores). El admin ve todos."""
    query = db.query(models.Mesocycle).options(
        joinedload(models.Mesocycle.created_by_coach)
    ).filter(models.Mesocycle.is_template == True)
    if current_user.role != "admin":
        query = query.filter(models.Mesocycle.created_by_coach_id == current_user.id)
    return [_plan_summary(db, p) for p in query.order_by(models.Mesocycle.created_at.desc()).all()]


@app.get("/plans/catalog", response_model=List[schemas.PlanSummaryResponse])
def list_plan_catalog(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Catálogo público (para cualquier usuario autenticado): solo planes publicados."""
    planes = (
        db.query(models.Mesocycle)
        .options(joinedload(models.Mesocycle.created_by_coach))
        .filter(models.Mesocycle.is_template == True, models.Mesocycle.is_published == True)
        .order_by(models.Mesocycle.created_at.desc())
        .all()
    )
    return [_plan_summary(db, p) for p in planes]


@app.get("/plans/{plan_id}")
def get_plan_detail(
    plan_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """El autor/admin ve el contenido COMPLETO (lo necesita para editarlo). Cualquier otro
    usuario autenticado — típicamente un atleta viendo el catálogo antes de comprarlo — recibe
    una VISTA PREVIA (schemas.PlanPreviewResponse): se ven los bloques y cuántos ejercicios trae
    cada día, pero no los ejercicios/series/pesos exactos. Mostrar la programación completa
    antes de pagar no tendría sentido comercial."""
    plan = db.query(models.Mesocycle).options(
        joinedload(models.Mesocycle.sessions).joinedload(models.Session.sets).joinedload(models.Set.exercise)
    ).filter(models.Mesocycle.id == plan_id, models.Mesocycle.is_template == True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    es_autor = plan.created_by_coach_id == current_user.id or current_user.role == "admin"
    if not plan.is_published and not es_autor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este plan todavía no está publicado")

    plan.sessions.sort(key=lambda s: (s.day_offset if s.day_offset is not None else 0))
    for sesion in plan.sessions:
        sesion.sets.sort(key=lambda x: x.set_order)

    if es_autor:
        return schemas.MesocycleFullResponse.model_validate(plan)

    sesiones_preview = []
    for sesion in plan.sessions:
        bloques_del_dia: list[str] = []
        ejercicios_del_dia: set = set()
        for s in sesion.sets:
            if s.block and s.block not in bloques_del_dia:
                bloques_del_dia.append(s.block)
            if s.exercise_id:
                ejercicios_del_dia.add(s.exercise_id)
        sesiones_preview.append(schemas.PlanSessionPreview(
            id=sesion.id,
            day_offset=sesion.day_offset,
            blocks=bloques_del_dia,
            exercise_count=len(ejercicios_del_dia),
        ))

    return schemas.PlanPreviewResponse(
        id=plan.id,
        name=plan.name,
        discipline=plan.discipline,
        start_date=plan.start_date,
        end_date=plan.end_date,
        description=plan.description,
        level=plan.level,
        has_cover_image=plan.has_cover_image,
        sessions=sesiones_preview,
    )


@app.put("/plans/{plan_id}/publish", response_model=schemas.PlanSummaryResponse)
def publish_plan(
    plan_id: UUID,
    req: schemas.PlanPublishUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    plan = _get_owned_plan(db, plan_id, current_user)
    if req.is_published:
        tiene_ejercicios = (
            db.query(models.Set)
            .join(models.Session, models.Set.session_id == models.Session.id)
            .filter(models.Session.mesocycle_id == plan.id)
            .count()
        )
        if not tiene_ejercicios:
            raise HTTPException(
                status_code=400,
                detail="No puedes publicar un plan sin ejercicios. Agrégalos primero.",
            )
    plan.is_published = req.is_published
    db.commit()
    db.refresh(plan)
    return _plan_summary(db, plan)


@app.delete("/plans/{plan_id}")
def delete_plan(plan_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(require_coach)):
    plan = _get_owned_plan(db, plan_id, current_user)
    db.delete(plan)
    db.commit()
    return {"message": "Plan eliminado correctamente"}


@app.post("/plans/{plan_id}/sessions/{session_id}/sets")
def add_set_to_plan_session(
    plan_id: UUID,
    session_id: UUID,
    req: schemas.PlanSetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Agrega un ejercicio a un día del plan. La carga puede ir en kg fijos o en % de 1RM
    (el % se resuelve a kg cuando un atleta adquiere el plan, usando SUS marcas)."""
    plan = _get_owned_plan(db, plan_id, current_user)

    sesion = db.query(models.Session).filter(
        models.Session.id == session_id, models.Session.mesocycle_id == plan.id
    ).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Ese día no pertenece a este plan")

    ejercicio = _get_or_create_exercise(db, req.exercise_name)
    series_actuales = db.query(models.Set).filter(models.Set.session_id == sesion.id).count()

    for i in range(req.prescribed_sets):
        db.add(models.Set(
            session_id=sesion.id,
            exercise_id=ejercicio.id,
            set_order=series_actuales + i + 1,
            prescribed_reps=req.prescribed_reps,
            rpe=req.rpe,
            prescribed_weight=req.prescribed_weight,
            prescribed_percentage=req.prescribed_percentage,
            reference_exercise=req.reference_exercise,
            block=req.block,
        ))

    db.commit()
    return {"message": f"'{req.exercise_name}' agregado al plan ({req.prescribed_sets} series)"}


@app.delete("/plans/{plan_id}/sets/{set_id}")
def delete_set_from_plan(
    plan_id: UUID,
    set_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    plan = _get_owned_plan(db, plan_id, current_user)
    db_set = (
        db.query(models.Set)
        .join(models.Session, models.Set.session_id == models.Session.id)
        .filter(models.Set.id == set_id, models.Session.mesocycle_id == plan.id)
        .first()
    )
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie no encontrada en este plan")
    db.delete(db_set)
    db.commit()
    return {"message": "Serie eliminada del plan"}


def _resolver_peso(porcentaje: float | None, peso_fijo: float | None, referencia: str, prs: dict) -> float | None:
    """Convierte un % de 1RM a kg usando las marcas del atleta, redondeando a múltiplos de 2.5kg.
    Si el plan traía un peso fijo se respeta; si no hay marca de referencia, queda sin peso
    (el atleta o su coach lo ajusta a mano)."""
    if porcentaje is None:
        return peso_fijo
    pr = prs.get(referencia.strip().lower())
    if not pr:
        return None
    return round((pr * porcentaje / 100) / 2.5) * 2.5


@app.post("/plans/{plan_id}/acquire")
def acquire_plan(
    plan_id: UUID,
    req: schemas.PlanAcquireRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """El atleta adquiere un plan publicado: se clona a un mesociclo propio con las fechas
    reales a partir de `start_date` y las cargas en % resueltas con SUS marcas de 1RM."""
    plan = db.query(models.Mesocycle).options(
        joinedload(models.Mesocycle.sessions).joinedload(models.Session.sets).joinedload(models.Set.exercise)
    ).filter(models.Mesocycle.id == plan_id, models.Mesocycle.is_template == True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if not plan.is_published:
        raise HTTPException(status_code=400, detail="Este plan todavía no está disponible")

    prs = {
        pr.exercise_name.strip().lower(): pr.max_weight_kg
        for pr in db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == current_user.id).all()
    }

    nuevo_meso = models.Mesocycle(
        user_id=current_user.id,
        is_template=False,
        source_plan_id=plan.id,
        name=plan.name,
        discipline=plan.discipline,
        start_date=req.start_date,
        ai_prompt_context=plan.description,
    )
    db.add(nuevo_meso)
    db.flush()

    max_offset = 0
    sin_marca = set()

    for sesion_plan in sorted(plan.sessions, key=lambda s: (s.day_offset if s.day_offset is not None else 0)):
        offset = sesion_plan.day_offset
        if offset is None:
            offset = (sesion_plan.scheduled_date - PLAN_EPOCH).days
        max_offset = max(max_offset, offset)

        nueva_sesion = models.Session(
            mesocycle_id=nuevo_meso.id,
            scheduled_date=req.start_date + timedelta(days=offset),
            athlete_notes=sesion_plan.athlete_notes,
            status="pending",
            duration_minutes=sesion_plan.duration_minutes,
        )
        db.add(nueva_sesion)
        db.flush()

        for set_plan in sorted(sesion_plan.sets, key=lambda x: x.set_order):
            referencia = set_plan.reference_exercise or (set_plan.exercise.name if set_plan.exercise else "")
            peso = _resolver_peso(set_plan.prescribed_percentage, set_plan.prescribed_weight, referencia, prs)
            if set_plan.prescribed_percentage and peso is None and referencia:
                sin_marca.add(referencia)

            db.add(models.Set(
                session_id=nueva_sesion.id,
                exercise_id=set_plan.exercise_id,
                set_order=set_plan.set_order,
                block=set_plan.block,
                prescribed_reps=set_plan.prescribed_reps,
                rpe=set_plan.rpe,
                prescribed_weight=peso,
                prescribed_percentage=set_plan.prescribed_percentage,
                reference_exercise=set_plan.reference_exercise,
            ))

    nuevo_meso.end_date = req.start_date + timedelta(days=max_offset)
    db.commit()

    mensaje = f"¡Plan '{plan.name}' adquirido! Ya está en tus entrenamientos a partir del {req.start_date}."
    if sin_marca:
        mensaje += (
            " Ojo: no tienes marcas registradas de "
            + ", ".join(sorted(sin_marca))
            + ", así que esas cargas quedaron sin kg (registra tus 1RM y ajústalas)."
        )
    return {"message": mensaje, "mesocycle_id": str(nuevo_meso.id), "missing_prs": sorted(sin_marca)}
