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
    if current_user.role == "admin":
        return grupo
    # El dueño del box gestiona todos los grupos de su box (los suyos, los generales y los de
    # sus coaches); un coach, solo los que él creó.
    if current_user.role == "owner" and grupo.box_id is not None and grupo.box_id == current_user.box_id:
        return grupo
    if grupo.coach_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Este grupo no te pertenece")
    return grupo


def ensure_athletes_addable(atletas: list[models.User], current_user: models.User) -> None:
    """Un coach solo puede agregar a su grupo atletas DE SU BOX y SIN afiliación (coach_id
    None) o que ya sean suyos -- si no, cualquier coach podría "adoptar" al atleta de otro coach
    (o de otro box) con solo conocer su ID (agregándolo a un grupo propio) y ganar acceso
    completo a su mesociclo, marcas, fitness level, etc. vía ensure_owner_or_coach /
    _coach_athlete_ids. El dueño del box puede agregar a cualquier atleta de su box. Admin puede
    agregar a cualquiera (gestión de la plataforma)."""
    if current_user.role == "admin":
        return
    otro_box = [a for a in atletas if a.box_id is None or a.box_id != current_user.box_id]
    if otro_box:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Uno o más atletas no pertenecen a tu box",
        )
    if current_user.role == "owner":
        return
    no_permitidos = [a for a in atletas if a.coach_id not in (None, current_user.id)]
    if no_permitidos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Uno o más atletas ya pertenecen a otro coach y no pueden agregarse a este grupo",
        )
