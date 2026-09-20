from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.common import FormatoWod, SanitizedModel
from backend.schemas.sets import SetResponse


# --- ESQUEMAS PARA SESIONES ---
class SessionCreate(SanitizedModel):
    mesocycle_id: UUID
    scheduled_date: date


class SessionResponse(BaseModel):
    id: UUID
    mesocycle_id: UUID
    scheduled_date: date
    completed_date: Optional[datetime] = None
    athlete_notes: Optional[str] = None
    status: str
    parent_session_id: Optional[UUID] = None  # si no es None, es una versión adaptada de otra sesión
    duration_minutes: Optional[int] = None
    day_offset: Optional[int] = None  # "día N" del plan (solo en plantillas)
    block_order: Optional[str] = None  # ej. "warmup,strength,metcon" — ver models.py:Session
    warmup_notes: Optional[str] = None
    # --- resultado del WOD/metcon, ver models.py:Session ---
    wod_format: Optional[str] = None
    wod_time_cap_seconds: Optional[int] = None
    wod_time_seconds: Optional[int] = None
    wod_rounds: Optional[int] = None
    wod_extra_reps: Optional[int] = None
    wod_emom_completed: Optional[bool] = None
    wod_calories: Optional[float] = None
    wod_distance_meters: Optional[float] = None
    wod_watts: Optional[float] = None
    sets: List[SetResponse] = []  # ¡Aquí anidamos los sets!

    class Config:
        from_attributes = True


class WodFormatUpdate(SanitizedModel):
    """El coach marca (o quita, mandando null) qué formato de WOD tiene esta sesión, y
    opcionalmente el timer: cap duro para "for_time", duración de la ventana para
    amrap/amrap_reps/calories/distance/watts. No aplica a emom/1rm."""
    wod_format: FormatoWod | None = None
    time_cap_seconds: int | None = Field(None, ge=1, le=36_000)


class SessionCompleteRequest(SanitizedModel):
    """Lo que el atleta reporta al terminar una sesión, si tenía un formato de WOD prescrito.
    Todo opcional: una sesión sin wod_format (o sin metcon) se completa sin mandar nada de esto."""
    wod_time_seconds: int | None = Field(None, ge=1, le=36_000)
    wod_rounds: int | None = Field(None, ge=0, le=500)
    wod_extra_reps: int | None = Field(None, ge=0, le=2000)
    wod_emom_completed: bool | None = None
    wod_calories: float | None = Field(None, ge=0, le=5000)
    wod_distance_meters: float | None = Field(None, ge=0, le=200_000)
    wod_watts: float | None = Field(None, ge=0, le=3000)


# --- ESQUEMA PARA ADAPTAR UNA SESIÓN AL TIEMPO DISPONIBLE ---
class SessionAdaptRequest(SanitizedModel):
    available_minutes: int = Field(..., ge=10, le=180)


class SessionMetaUpdate(SanitizedModel):
    """Metadatos de la sesión que el coach puede ajustar aparte de sus series: en qué orden se
    muestran los bloques, y las pautas de calentamiento. Ambos opcionales -- cada uno se guarda
    solo si vino en la petición, igual que UserPreferencesUpdate."""
    block_order: str | None = Field(None, max_length=200)
    warmup_notes: str | None = Field(None, max_length=1000)
