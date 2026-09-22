"""Verificación de pertenencia de un grupo — usado por groups.py y también por
mesocycles.py/ai.py al programar un mesociclo para un grupo completo (necesitan validar la
misma pertenencia antes de tocarlo)."""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend import models


def get_owned_group(db: Session, group_id: UUID, current_user: models.User) -> models.Group:
    grupo = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if current_user.role != "admin" and grupo.coach_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este grupo no te pertenece")
    return grupo


def ensure_athletes_addable(atletas: list[models.User], current_user: models.User) -> None:
    """Un coach solo puede agregar a su grupo atletas SIN afiliación (coach_id None) o que ya
    sean suyos -- si no, cualquier coach podría "adoptar" al atleta de otro coach con solo
    conocer su ID (agregándolo a un grupo propio) y ganar acceso completo a su mesociclo,
    marcas, fitness level, etc. vía ensure_owner_or_coach/_coach_athlete_ids. Admin puede
    agregar a cualquiera (gestión de la plataforma)."""
    if current_user.role == "admin":
        return
    no_permitidos = [a for a in atletas if a.coach_id not in (None, current_user.id)]
    if no_permitidos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Uno o más atletas ya pertenecen a otro coach y no pueden agregarse a este grupo",
        )
