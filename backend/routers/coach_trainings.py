"""Los entrenos del coach, todos juntos (pantalla "Entrenos"). Ver services/entrenos.py."""
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.errors import SolicitudInvalida
from backend.core.security import require_coach
from backend.database import get_db
from backend.services.entrenos import MAX_DIAS_DEL_RANGO, entrenos_del_coach

router = APIRouter(prefix="/coach", tags=["coach"])


@router.get("/trainings", response_model=List[schemas.CoachTrainingItem])
def listar_entrenos(
    date_from: date = Query(..., description="Primer día (incluido)"),
    date_to: date = Query(..., description="Último día (incluido)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_coach),
):
    """Todo lo que el coach programó entre dos fechas, para sus grupos y para sus atletas personalizados.
    Un día de un grupo es UN entreno (con cuántos de sus miembros ya lo terminaron); uno personalizado es el
    de ese atleta. Sirve tanto para la vista de lista como para la de calendario."""
    if date_to < date_from:
        raise SolicitudInvalida("La fecha final no puede ser anterior a la inicial.")
    if (date_to - date_from).days > MAX_DIAS_DEL_RANGO:
        raise SolicitudInvalida(f"Pide como máximo {MAX_DIAS_DEL_RANGO} días a la vez.")
    return entrenos_del_coach(db, current_user, date_from, date_to)
