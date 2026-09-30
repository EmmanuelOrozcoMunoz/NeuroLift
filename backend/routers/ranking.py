"""Ranking del box entre atletas: marcas (1RM) y WODs. Ver backend/services/ranking.py."""
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.errors import Prohibido
from backend.core.security import get_current_user
from backend.database import get_db
from backend.services import ranking as servicio

router = APIRouter(prefix="/ranking", tags=["ranking"])

Sexo = Optional[Literal["male", "female"]]


def _box_del_ranking(user: models.User) -> UUID:
    """El ranking es de una cuenta con varios atletas (un box o un coach independiente), y lo ven
    sus atletas y sus entrenadores. No existe para un atleta solo ni para el admin."""
    if user.role not in ("athlete", *models.COACHING_ROLES) or user.box is None or not user.box.is_active:
        raise Prohibido("El ranking es de tu box")
    if user.box.kind not in ("box", "coach"):
        raise Prohibido("El ranking es de tu box")
    return user.box.id


@router.get("/lifts", response_model=List[schemas.RankingLift])
def listar_levantamientos(
    sex: Sexo = Query(None), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Levantamientos con marcas de los atletas de tu box que aparecen en el ranking."""
    return servicio.levantamientos(db, _box_del_ranking(current_user), sex)


@router.get("/lifts/{key}", response_model=List[schemas.RankingLiftRow])
def tabla_de_un_levantamiento(
    key: str, sex: Sexo = Query(None), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Ranking de un levantamiento (la mejor marca de cada atleta), de mayor a menor."""
    return servicio.tabla_de_marcas(db, _box_del_ranking(current_user), key, current_user.id, sex)


@router.get("/wods", response_model=List[schemas.RankingWod])
def listar_wods(
    sex: Sexo = Query(None), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """WODs que atletas de tu box anotaron a mano con resultado."""
    return servicio.wods(db, _box_del_ranking(current_user), sex)


@router.get("/wods/{key}", response_model=List[schemas.RankingWodRow])
def tabla_de_un_wod(
    key: str,
    wod_format: str = Query(..., min_length=1, max_length=20),
    sex: Sexo = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Ranking de un WOD y formato (el mejor intento de cada atleta), del mejor al peor resultado."""
    return servicio.tabla_de_wod(db, _box_del_ranking(current_user), key, wod_format, current_user.id, sex)
