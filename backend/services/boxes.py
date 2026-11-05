"""Reglas de boxes que comparten varios routers."""
from datetime import datetime

from sqlalchemy.orm import Session

from backend import models
from backend.core.errors import SolicitudInvalida
from backend.core.invite import new_invite_code


def find_active_box_by_code(db: Session, code: str | None) -> models.Box:
    """Box activo con ese código de invitación, o 400. Lo usan el registro (/auth/register), la
    consulta pública (GET /boxes/by-code) y unirse a un box (POST /boxes/join)."""
    normalizado = (code or "").strip().upper()
    if not normalizado:
        raise SolicitudInvalida("Necesitas el código de tu box para crear tu cuenta. Pídeselo a tu coach.")
    box = db.query(models.Box).filter(models.Box.invite_code == normalizado).first()
    # La cuenta personal de un atleta solo no admite a nadie más (su código es interno)
    if not box or not box.is_active or box.kind == "athlete":
        raise SolicitudInvalida("Ese código de box no es válido o el box no está activo.")
    return box


def crear_cuenta_personal(db: Session, nombre: str) -> models.Box:
    """La cuenta gratuita de un atleta solo (Box kind="athlete"): sin dueño ni coach, con un único
    miembro. La usan el registro sin código y "sacar a un atleta de la cuenta"."""
    cuenta = models.Box(
        name=nombre,
        kind="athlete",
        status="active",
        approved_at=datetime.utcnow(),
        invite_code=new_invite_code(db),
    )
    db.add(cuenta)
    db.flush()
    return cuenta


def sacar_atleta_de_la_cuenta(db: Session, atleta: models.User, accion: str) -> int:
    """Deja al atleta sin box ni coach, como si se hubiera registrado solo: vuelve a su cuenta
    personal y conserva su cuenta, sus marcas y su historial. Puede unirse después a otro coach o
    box con su código (POST /boxes/join).

    - Sale de todos los grupos donde estaba.
    - Los borradores que el coach tenía a medias para él se borran (el atleta nunca los vio).
    - `accion` decide qué pasa con lo que el coach le programó: "desvincular" lo conserva como
      programas individuales; "eliminar" lo borra. Lo que el atleta anotó por su cuenta no se toca.
    Devuelve cuántos programas del coach tenía."""
    from backend.services.groups import retirar_miembro

    grupos = (
        db.query(models.Group)
        .join(models.group_members, models.group_members.c.group_id == models.Group.id)
        .filter(models.group_members.c.user_id == atleta.id)
        .all()
    )
    for grupo in grupos:
        retirar_miembro(db, grupo, atleta.id, accion)

    propios = db.query(models.Mesocycle).filter(
        models.Mesocycle.user_id == atleta.id, models.Mesocycle.is_template.is_(False)
    ).all()
    programados = 0
    for meso in propios:
        if meso.is_draft:
            db.delete(meso)
        elif not meso.is_self_managed and not meso.is_class_log:
            programados += 1
            if accion == "eliminar":
                db.delete(meso)

    cuenta = crear_cuenta_personal(db, atleta.full_name)
    atleta.box_id = cuenta.id
    atleta.coach_id = None
    return programados
