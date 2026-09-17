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
