"""Boxes (gimnasios cliente): alta pública, perfil, logo, código de invitación y gestión de
miembros por parte del dueño. La aprobación de boxes nuevos vive en routers/admin.py."""
import secrets
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session, joinedload

from backend import avatars, models, schemas, storage
from backend.core.logging import security_logger
from backend.core.security import (
    _client_ip,
    _ip_and_user_key,
    get_current_user,
    get_password_hash,
    limiter,
    require_owner,
)
from backend.database import get_db
from backend.routers.auth import find_active_box_by_code

router = APIRouter(prefix="/boxes", tags=["boxes"])

BOX_REGISTER_MESSAGE = (
    "Recibimos la solicitud de tu box. Te avisaremos en cuanto esté aprobado; mientras tanto ya "
    "puedes iniciar sesión para completar su perfil."
)
# Sin 0/O ni 1/I: el código se dicta en voz alta o se copia de una pantalla
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_invite_code(db: Session) -> str:
    """Código de 8 caracteres (32^8 ≈ 10^12 combinaciones: no se adivina probando)."""
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
        if not db.query(models.Box.id).filter(models.Box.invite_code == code).first():
            return code


def _box_detail(box: models.Box, viewer: models.User) -> schemas.BoxDetail:
    detalle = schemas.BoxDetail.model_validate(box)
    # El código de invitación lo reparten el dueño y los coaches; un atleta no lo necesita
    if viewer.role not in models.COACHING_ROLES:
        detalle.invite_code = None
    return detalle


# ------------------------------------------------------------------------ públicos

@router.post("/register", response_model=schemas.MessageResponse)
@limiter.limit("3/hour")
def register_box(request: Request, req: schemas.BoxRegister, db: Session = Depends(get_db)):
    """Alta pública: crea el box en estado "pending" y la cuenta de su dueño (rol owner). El
    admin de plataforma lo aprueba desde su panel; hasta entonces el dueño puede entrar y
    completar el perfil, pero no programar ni recibir atletas.

    Igual que /auth/register, responde lo mismo exista o no ya ese correo (no enumera cuentas):
    si ya existía, simplemente no se crea nada."""
    existente = db.query(models.User).filter(models.User.email == req.email).first()
    hashed_password = get_password_hash(req.password)

    if not existente:
        box = models.Box(
            name=req.box_name,
            address=req.address,
            city=req.city,
            state=req.state,
            country=req.country,
            status="pending",
            invite_code=new_invite_code(db),
        )
        db.add(box)
        db.flush()
        db.add(models.User(
            email=req.email,
            full_name=req.owner_name,
            hashed_password=hashed_password,
            role="owner",
            box_id=box.id,
        ))
        db.commit()
        security_logger.info(
            "Box registrado (pendiente): '%s' por %s desde %s", req.box_name, req.email, _client_ip(request)
        )

    return {"message": BOX_REGISTER_MESSAGE}


@router.get("/by-code/{code}", response_model=schemas.BoxPublicInfo)
@limiter.limit("30/minute")
def get_box_by_invite_code(request: Request, code: str, db: Session = Depends(get_db)):
    """Para que el registro de atleta confirme "te vas a unir a CrossFit Norte" antes de enviar."""
    return find_active_box_by_code(db, code)


# ------------------------------------------------------------- perfil del box

@router.get("/me", response_model=schemas.BoxDetail)
def get_my_box(current_user: models.User = Depends(get_current_user)):
    if current_user.box is None:
        raise HTTPException(status_code=404, detail="No perteneces a ningún box")
    return _box_detail(current_user.box, current_user)


@router.put("/me", response_model=schemas.BoxDetail)
def update_my_box(
    req: schemas.BoxUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(require_owner)
):
    box = current_user.box
    cambios = req.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        if campo == "name" and not valor:
            continue  # el nombre no se puede borrar
        setattr(box, campo, valor)
    db.commit()
    db.refresh(box)
    return _box_detail(box, current_user)


@router.post("/me/logo", response_model=schemas.BoxDetail)
@limiter.limit("10/hour", key_func=_ip_and_user_key)
async def upload_box_logo(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_owner),
):
    """Sube (o reemplaza) la foto/logo del box — mismo pipeline de saneo que el avatar."""
    box = current_user.box
    raw = await avatars.read_and_validate_upload(file)
    clean_bytes, extension = avatars.rerender_and_strip_metadata(raw)

    nombre_anterior = box.logo_filename
    box.logo_filename = storage.upload_object(
        storage.BOX_LOGO_BUCKET, clean_bytes, extension, avatars.AVATAR_CONTENT_TYPES[extension]
    )
    db.commit()
    db.refresh(box)
    storage.delete_object(storage.BOX_LOGO_BUCKET, nombre_anterior)
    return _box_detail(box, current_user)


@router.delete("/me/logo", response_model=schemas.MessageResponse)
def delete_box_logo(db: Session = Depends(get_db), current_user: models.User = Depends(require_owner)):
    box = current_user.box
    if not box.logo_filename:
        raise HTTPException(status_code=404, detail="Tu box no tiene foto.")
    storage.delete_object(storage.BOX_LOGO_BUCKET, box.logo_filename)
    box.logo_filename = None
    db.commit()
    return {"message": "Foto del box eliminada."}


@router.get("/{box_id}/logo")
def get_box_logo(box_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Cualquier miembro del box (o el admin de plataforma) puede ver su logo."""
    if current_user.role != "admin" and current_user.box_id != box_id:
        raise HTTPException(status_code=403, detail="No perteneces a este box")
    box = db.query(models.Box).filter(models.Box.id == box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail="Box no encontrado")
    return storage.redirect_to_image(storage.BOX_LOGO_BUCKET, box.logo_filename)


@router.post("/me/invite-code", response_model=schemas.BoxDetail)
def rotate_invite_code(db: Session = Depends(get_db), current_user: models.User = Depends(require_owner)):
    """Genera un código nuevo: el link anterior deja de funcionar (útil si se filtró). Los
    atletas que ya se registraron no se ven afectados."""
    box = current_user.box
    box.invite_code = new_invite_code(db)
    db.commit()
    db.refresh(box)
    return _box_detail(box, current_user)


# ---------------------------------------------------------------- miembros

@router.get("/me/members", response_model=List[schemas.BoxMember])
def list_box_members(
    role: Optional[Literal["athlete", "coach", "owner"]] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_owner),
):
    query = (
        db.query(models.User)
        .options(joinedload(models.User.coach))
        .filter(models.User.box_id == current_user.box_id)
    )
    if role:
        query = query.filter(models.User.role == role)
    return [
        schemas.BoxMember(
            id=u.id,
            full_name=u.full_name,
            email=u.email,
            role=u.role,
            has_avatar=u.has_avatar,
            coach_id=u.coach_id,
            coach_name=u.coach.full_name if u.coach else None,
            created_at=u.created_at,
        )
        for u in query.order_by(models.User.full_name).all()
    ]


@router.post("/me/coaches", response_model=schemas.BoxMember)
@limiter.limit("20/hour", key_func=_ip_and_user_key)
def create_box_coach(
    request: Request,
    req: schemas.CoachCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_owner),
):
    """El dueño da de alta a un coach de su box. Aquí SÍ se avisa si el correo ya existe: quien
    llama es el dueño autenticado de un box (no un anónimo), el endpoint va limitado por hora, y
    sin el aviso no tendría forma de saber por qué su coach no puede entrar."""
    if not current_user.box.is_active:
        raise HTTPException(status_code=403, detail="Podrás agregar coaches cuando tu box esté aprobado.")
    if db.query(models.User.id).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo.")

    coach = models.User(
        email=req.email,
        full_name=req.full_name,
        hashed_password=get_password_hash(req.password),
        role="coach",
        box_id=current_user.box_id,
    )
    db.add(coach)
    db.commit()
    db.refresh(coach)
    security_logger.info("Coach creado: dueño=%s creó a %s en box=%s", current_user.email, coach.email, coach.box_id)
    return schemas.BoxMember(
        id=coach.id, full_name=coach.full_name, email=coach.email, role=coach.role, created_at=coach.created_at
    )


@router.put("/me/athletes/{athlete_id}/coach", response_model=schemas.BoxMember)
def assign_athlete_coach(
    athlete_id: UUID,
    req: schemas.AthleteCoachAssign,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_owner),
):
    """Asigna (o quita) el coach de un atleta del box. Sin coach, el atleta queda "del box" y
    recibe los mesociclos generales que el dueño programe a los grupos donde lo incluya."""
    atleta = db.query(models.User).filter(
        models.User.id == athlete_id,
        models.User.box_id == current_user.box_id,
        models.User.role == "athlete",
    ).first()
    if not atleta:
        raise HTTPException(status_code=404, detail="Atleta no encontrado en tu box")

    coach = None
    if req.coach_id is not None:
        coach = db.query(models.User).filter(
            models.User.id == req.coach_id,
            models.User.box_id == current_user.box_id,
            models.User.role.in_(models.COACHING_ROLES),
        ).first()
        if not coach:
            raise HTTPException(status_code=400, detail="Ese coach no pertenece a tu box")

    atleta.coach_id = coach.id if coach else None
    db.commit()
    return schemas.BoxMember(
        id=atleta.id,
        full_name=atleta.full_name,
        email=atleta.email,
        role=atleta.role,
        has_avatar=atleta.has_avatar,
        coach_id=atleta.coach_id,
        coach_name=coach.full_name if coach else None,
        created_at=atleta.created_at,
    )
