"""Token para restablecer la contraseña: un JWT firmado, de un solo uso y de vida corta.

No hay tabla ni migración: el token lleva una huella de la contraseña actual (`pw`), así que en cuanto la
contraseña cambia, ese token y cualquier otro emitido antes dejan de servir. No lleva `sub` ni `role`, así
que tampoco sirve como token de sesión (get_current_user lo rechaza), y un token de sesión no sirve aquí
porque le falta `purpose`."""
import hashlib
from datetime import datetime, timedelta

import jwt
from jwt import PyJWTError
from sqlalchemy.orm import Session

from backend import models
from backend.core.config import ALGORITHM, FRONTEND_URL, RESET_TOKEN_MINUTES, SECRET_KEY

_PROPOSITO = "reset-password"


def _huella(hashed_password: str) -> str:
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


def crear_token(usuario: models.User) -> str:
    return jwt.encode(
        {
            "purpose": _PROPOSITO,
            "uid": str(usuario.id),
            "pw": _huella(usuario.hashed_password),
            "exp": datetime.utcnow() + timedelta(minutes=RESET_TOKEN_MINUTES),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def enlace_de_recuperacion(usuario: models.User) -> str:
    return f"{FRONTEND_URL}/restablecer?token={crear_token(usuario)}"


def usuario_del_token(db: Session, token: str) -> models.User | None:
    """El usuario al que pertenece un token vigente y sin usar, o None."""
    try:
        datos = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        return None
    if datos.get("purpose") != _PROPOSITO or not datos.get("uid"):
        return None
    usuario = db.query(models.User).filter(models.User.id == datos["uid"]).first()
    if usuario is None or datos.get("pw") != _huella(usuario.hashed_password):
        return None
    return usuario
