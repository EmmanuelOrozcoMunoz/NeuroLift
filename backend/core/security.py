from datetime import datetime, timedelta
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from backend import models
from backend.core.config import ALGORITHM, SECRET_KEY
from backend.database import get_db

# Le decimos a FastAPI dónde está la ruta de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Vive aquí (no en main.py) para que los routers puedan usar @limiter.limit(...) en sus propios
# módulos sin crear un import circular con main.py (que es quien lo registra en app.state).
limiter = Limiter(key_func=get_remote_address)


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


def ensure_owner_or_coach_editable(db: Session, mesocycle: models.Mesocycle, current_user: models.User):
    """Como ensure_owner_or_coach, pero además: si quien edita ES el propio atleta (no su coach
    ni un admin), solo puede hacerlo sobre un mesociclo que él mismo creó a mano
    (is_self_managed) -- uno que le prescribió su coach sigue siendo editable solo por el
    coach, aunque el atleta sea su "dueño" en el sentido de a quién pertenece."""
    ensure_owner_or_coach(db, mesocycle.user_id, current_user)
    if current_user.role == "athlete" and not mesocycle.is_self_managed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta sesión la prescribió tu coach — solo tu coach puede editarla",
        )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "?"


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
