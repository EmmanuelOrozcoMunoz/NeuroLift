from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.common import Dia, SanitizedModel
from backend.schemas.sessions import SessionResponse


# --- ESQUEMAS PARA MESOCICLOS ---
class MesocycleCreate(SanitizedModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date


class MesocycleResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    is_active: bool

    class Config:
        from_attributes = True


class MesocycleSummaryResponse(BaseModel):
    """GET /users/{id}/mesocycles/ — exactamente los campos que ya consume el frontend
    (ver web/src/lib/types.ts:MesocycleSummary). Antes este endpoint devolvía el modelo ORM
    crudo sin response_model; con esto queda con la misma lista blanca que el resto de la API."""
    id: UUID
    user_id: Optional[UUID] = None
    group_id: Optional[UUID] = None
    name: str | None = None
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    is_active: bool
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    level: Optional[str] = None

    class Config:
        from_attributes = True


class MesocycleFullResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None  # None en las plantillas de planes (no tienen dueño)
    name: str | None = None
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None
    level: Optional[str] = None
    price: Optional[float] = None  # solo relevante en planes (is_template) — None en mesociclos normales
    is_template: bool = False
    has_cover_image: bool = False  # true -> el cliente puede pedir GET /plans/{id}/cover
    is_preview: bool = False  # ver PlanPreviewResponse: esta es SIEMPRE la versión completa
    sessions: List[SessionResponse] = []  # ¡Aquí anidamos las sesiones!

    class Config:
        from_attributes = True


class MesocycleManualCreate(SanitizedModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date
    weeks_count: int = Field(..., ge=1, le=52)
    training_days: List[Dia]  # 0 = Lunes, 1 = Martes ... 6 = Domingo


class MesocycleManualGroupCreate(SanitizedModel):
    group_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date
    weeks_count: int = Field(..., ge=1, le=52)
    training_days: List[Dia]
