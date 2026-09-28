from datetime import date, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from backend.schemas.common import Dia, SanitizedModel
from backend.schemas.sessions import SessionResponse


def _dias_unicos(dias: Optional[List[int]]) -> Optional[List[int]]:
    return sorted(set(dias)) if dias is not None else None


class ClassCreate(SanitizedModel):
    """El dueño da de alta una clase recurrente del box y le asigna profesor."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    coach_id: Optional[UUID] = None
    weekdays: List[Dia] = Field(..., min_length=1, max_length=7)
    start_time: time
    duration_minutes: int = Field(60, ge=15, le=240)

    _dias = field_validator("weekdays")(_dias_unicos)


class ClassUpdate(SanitizedModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    # Para quitar el profesor, mandar clear_coach=true (None en coach_id = "no cambiar")
    coach_id: Optional[UUID] = None
    clear_coach: bool = False
    weekdays: Optional[List[Dia]] = Field(None, min_length=1, max_length=7)
    start_time: Optional[time] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=240)

    _dias = field_validator("weekdays")(_dias_unicos)


class ClassResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    coach_id: Optional[UUID] = None
    coach_name: Optional[str] = None
    weekdays: List[int]
    start_time: str  # "HH:MM"
    duration_minutes: int
    is_active: bool
    # Si quien pregunta puede programar el contenido de esta clase (su profesor o el dueño)
    can_program: bool = False


class ClassOccurrence(BaseModel):
    """Una clase en un día concreto del calendario: horario, profesor y lo que se va a hacer."""
    class_id: UUID
    class_name: str
    description: Optional[str] = None
    date: date
    start_time: str
    duration_minutes: int
    coach_id: Optional[UUID] = None
    coach_name: Optional[str] = None
    can_program: bool = False
    # Contenido que programó el profesor para ese día (None = todavía sin programar)
    session: Optional[SessionResponse] = None
    # Mesociclo de la clase que contiene esa sesión (para abrir el editor del profesor)
    program_mesocycle_id: Optional[UUID] = None
    program_name: Optional[str] = None
    # Registro del atleta que pregunta, si ya registró esta clase
    my_session_id: Optional[UUID] = None
    my_mesocycle_id: Optional[UUID] = None
    my_status: Optional[str] = None


class ClassProgramCreate(SanitizedModel):
    """Programar la clase "como un mesociclo": un bloque de varias semanas de una vez."""
    name: str = Field(..., min_length=1, max_length=100)
    start_date: date
    weeks_count: int = Field(..., ge=1, le=16)


class ClassDayCreate(SanitizedModel):
    """Programar la clase día por día: una sola sesión para una fecha."""
    date: date


class ClassProgramResponse(BaseModel):
    id: UUID
    name: str
    start_date: date
    end_date: Optional[date] = None
    sessions_count: int
    # Fechas que ya tenían contenido programado y se saltaron (para avisar al profesor)
    skipped_dates: List[date] = []


class ClassDayResponse(BaseModel):
    mesocycle_id: UUID
    session_id: UUID


class ClassJoinResponse(BaseModel):
    """Copia personal de la clase donde el atleta registra lo que hizo."""
    mesocycle_id: UUID
    session_id: UUID
    # Ejercicios con carga en % de 1RM que no se pudieron resolver (el atleta no tiene esa marca)
    missing_prs: List[str] = []
