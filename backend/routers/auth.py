from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from backend.core.logging import security_logger
from backend.core.security import (
    _client_ip,
    _optional_current_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    limiter,
    verify_password,
)
from backend.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

REGISTER_GENERIC_MESSAGE = "Si el correo no estaba registrado, tu cuenta fue creada. Ya puedes iniciar sesión."


@router.post("/register", response_model=schemas.MessageResponse)
@limiter.limit("5/minute")
def register_user(request: Request, user: schemas.UserRegister, db: Session = Depends(get_db)):
    """Alta de un atleta. Misma respuesta (mismo status, mismo cuerpo, mismo tiempo aproximado)
    exista o no ya una cuenta con ese correo — evita que alguien use este endpoint para enumerar
    qué correos están registrados en el sistema (ni por el contenido de la respuesta ni por
    temporización, ya que el hasheo bcrypt, intencionalmente lento, se ejecuta siempre).

    El box al que se une sale de:
    - quien lo registra, si es un coach/dueño YA autenticado (p. ej. "Registrar atleta" en su
      panel). Si es un coach, el atleta queda además ligado a él; si es el dueño, queda como
      atleta "del box" (sin coach) y el dueño le asigna coach después si quiere.
    - el código de invitación del box, si es un autoregistro. Un código inválido o de un box
      no activo SÍ se rechaza con un error explícito: el código es público (va en el link que
      comparte el box), así que decir "ese código no existe" no filtra nada de nadie."""
    creador = _optional_current_user(request, db)
    es_de_coach = (
        creador is not None
        and creador.role in models.COACHING_ROLES
        and creador.box is not None
        and creador.box.is_active
    )

    if es_de_coach:
        box = creador.box
        coach_id = creador.id if creador.role == "coach" else None
    else:
        box = find_active_box_by_code(db, user.invite_code)
        coach_id = None

    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    # Siempre se hashea la contraseña, se use o no, para que ambas rutas tarden lo mismo.
    hashed_password = get_password_hash(user.password)

    if not db_user:
        db.add(models.User(
            email=user.email,
            full_name=user.full_name,
            hashed_password=hashed_password,
            role="athlete",
            body_weight=user.body_weight,
            coach_id=coach_id,
            box_id=box.id,
        ))
        db.commit()

    return {"message": REGISTER_GENERIC_MESSAGE}


def find_active_box_by_code(db: Session, code: str | None) -> models.Box:
    """Box activo con ese código de invitación, o 400. Compartido con GET /boxes/by-code."""
    normalizado = (code or "").strip().upper()
    if not normalizado:
        raise HTTPException(
            status_code=400,
            detail="Necesitas el código de tu box para crear tu cuenta. Pídeselo a tu coach.",
        )
    box = db.query(models.Box).filter(models.Box.invite_code == normalizado).first()
    if not box or not box.is_active:
        raise HTTPException(status_code=400, detail="Ese código de box no es válido o el box no está activo.")
    return box


@router.post("/login")
@limiter.limit("10/minute")
def login_user(request: Request, credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    usuario = db.query(models.User).filter(models.User.email == credentials.email).first()

    if not usuario or not verify_password(credentials.password, usuario.hashed_password):
        security_logger.warning("Login fallido para email=%s desde %s", credentials.email, _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    # Solo el dueño entra con el box pendiente/rechazado/suspendido (ve el estado de su
    # solicitud); a sus coaches y atletas se les explica en vez de dejarlos entrar a una app
    # que les respondería 403 en cada pantalla (ver get_current_user).
    if usuario.box is not None and not usuario.box.is_active and usuario.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu box no está activo en este momento. Contacta a su administrador.",
        )

    security_logger.info("Login exitoso: %s (rol=%s) desde %s", usuario.email, usuario.role, _client_ip(request))

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": usuario.email, "role": usuario.role, "id": str(usuario.id), "tv": usuario.token_version},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/logout", response_model=schemas.MessageResponse)
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
