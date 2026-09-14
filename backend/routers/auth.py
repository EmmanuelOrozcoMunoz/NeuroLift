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
