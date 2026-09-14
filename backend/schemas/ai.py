from datetime import date
from typing import List
from uuid import UUID

from pydantic import Field

from backend.schemas.common import Dia, SanitizedModel


class AIGenerateRequest(SanitizedModel):
    mesocycle_id: UUID
    context: str = Field(..., min_length=1, max_length=2000)
    weeks_count: int = Field(..., ge=1, le=52)
    sessions_per_week: int = Field(..., ge=1, le=7)


class AIGenerateSmart(SanitizedModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date
    # Tope más bajo que en creación manual: cada 2 semanas dispara una llamada a Gemini,
    # así que 52 semanas serían ~26 llamadas encadenadas en un solo request.
    weeks_count: int = Field(..., ge=1, le=16)
    training_days: List[Dia]
    context: str = Field("", max_length=2000)
    session_duration_minutes: int | None = Field(None, ge=15, le=180)


class AIGenerateSmartGroup(SanitizedModel):
    group_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date
    # Mismo tope que la versión individual, y aquí se multiplica por cada atleta del grupo.
    weeks_count: int = Field(..., ge=1, le=16)
    training_days: List[Dia]
    context: str = Field("", max_length=2000)
    session_duration_minutes: int | None = Field(None, ge=15, le=180)
