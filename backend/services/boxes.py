"""Reglas de boxes que comparten varios routers."""
from sqlalchemy.orm import Session

from backend import models
from backend.core.errors import SolicitudInvalida


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
