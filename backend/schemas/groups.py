from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.common import Bloque, FormatoWod, SanitizedModel


# --- ESQUEMAS PARA GRUPOS DE ATLETAS ---
class GroupCreate(SanitizedModel):
    name: str = Field(..., min_length=1, max_length=100)
    athlete_ids: List[UUID] = []


class GroupMemberAdd(SanitizedModel):
    athlete_ids: List[UUID]


class GroupMemberResponse(BaseModel):
    id: UUID
    full_name: str
    email: str

    class Config:
        from_attributes = True


class GroupResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    has_cover_image: bool = False  # true -> el cliente puede pedir GET /groups/{id}/cover
    members: List[GroupMemberResponse] = []

    class Config:
        from_attributes = True


class GroupSummaryResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    member_count: int
    coach_name: str | None = None  # solo relevante cuando lo consulta un admin
    has_cover_image: bool = False


class GroupMesocycleAthlete(BaseModel):
    user_id: UUID
    full_name: str
    mesocycle_id: UUID
    is_active: bool


class GroupMesocycleProgram(BaseModel):
    """Un mesociclo programado para el grupo: mismo nombre/fechas, una instancia por atleta."""
    name: str
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    created_at: datetime
    athletes: List[GroupMesocycleAthlete] = []
    session_dates: List[date] = []  # calendario compartido (todos los atletas entrenan los mismos días)


class GroupSessionExerciseAdd(SanitizedModel):
    """Añade el mismo ejercicio a la sesión de una fecha dada, para TODOS los atletas del programa."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date
    scheduled_date: date
    exercise_name: str = Field(..., min_length=1, max_length=100)
    prescribed_sets: int = Field(3, ge=1, le=20)
    prescribed_reps: int = Field(..., ge=1, le=100)
    rpe: float | None = Field(None, ge=0, le=10)
    prescribed_weight: float | None = Field(None, ge=0, le=1000)
    # Pesos del WOD por categoría/género (bloque "metcon") — si se manda cualquiera de estos,
    # cada atleta recibe el que le corresponde según su categoría (rx/scaled) y sexo (ver
    # backend/routers/groups.py:_resolve_group_weight). Si ninguno viene, se usa
    # prescribed_weight para todos, igual que antes.
    prescribed_weight_rx_male: float | None = Field(None, ge=0, le=1000)
    prescribed_weight_rx_female: float | None = Field(None, ge=0, le=1000)
    prescribed_weight_scaled_male: float | None = Field(None, ge=0, le=1000)
    prescribed_weight_scaled_female: float | None = Field(None, ge=0, le=1000)
    # Carga en % de 1RM (bloques de fuerza/weightlifting) — cada atleta recibe su propio peso
    # calculado con SUS marcas ya registradas (ver backend/routers/shared.py:
    # resolve_weight_from_percentage). `reference_exercise` vacío usa el mismo ejercicio.
    prescribed_percentage: float | None = Field(None, ge=1, le=150)
    reference_exercise: str | None = Field(None, min_length=1, max_length=100)
    block: Bloque | None = None


class GroupSessionExerciseUpdate(SanitizedModel):
    """Actualiza (nombre/series/reps/RPE/peso) un ejercicio ya existente en la sesión de una fecha
    dada, para TODOS los atletas del programa. Se identifica el ejercicio por su nombre ACTUAL;
    si se reduce el número de series se borran las sobrantes, si se aumenta se crean nuevas."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date
    scheduled_date: date
    exercise_name: str = Field(..., min_length=1, max_length=100)
    new_exercise_name: str = Field(..., min_length=1, max_length=100)
    prescribed_sets: int = Field(..., ge=1, le=20)
    prescribed_reps: int = Field(..., ge=1, le=100)
    rpe: float | None = Field(None, ge=0, le=10)
    prescribed_weight: float | None = Field(None, ge=0, le=1000)
    prescribed_weight_rx_male: float | None = Field(None, ge=0, le=1000)
    prescribed_weight_rx_female: float | None = Field(None, ge=0, le=1000)
    prescribed_weight_scaled_male: float | None = Field(None, ge=0, le=1000)
    prescribed_weight_scaled_female: float | None = Field(None, ge=0, le=1000)
    prescribed_percentage: float | None = Field(None, ge=1, le=150)
    reference_exercise: str | None = Field(None, min_length=1, max_length=100)
    block: Bloque | None = None


class GroupSessionExerciseDelete(SanitizedModel):
    """Elimina por completo un ejercicio (todas sus series) de la sesión de una fecha dada,
    para TODOS los atletas del programa."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date
    scheduled_date: date
    exercise_name: str = Field(..., min_length=1, max_length=100)


class GroupProgramDelete(SanitizedModel):
    """Elimina el programa completo: el mesociclo (con todas sus sesiones y series) de CADA
    atleta del grupo que lo tenga asignado."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date


class GroupSessionWodFormatUpdate(SanitizedModel):
    """El coach fija el formato de WOD (y su timer/time cap) UNA sola vez para la sesión de una
    fecha dada, aplicado a TODOS los atletas del programa a la vez — evita repetir la misma
    acción atleta por atleta cuando todo el grupo hace el mismo WOD."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date
    scheduled_date: date
    wod_format: FormatoWod | None = None
    time_cap_seconds: int | None = Field(None, ge=1, le=36_000)


class GroupSessionWodNotesUpdate(SanitizedModel):
    """El coach escribe la descripción libre del WOD (texto plano) UNA sola vez para la sesión
    de una fecha dada, aplicado a TODOS los atletas del programa a la vez — mismo motivo que
    GroupSessionWodFormatUpdate, para el bloque Metabólico/WOD (ver WodBlockCard en el frontend)."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date
    scheduled_date: date
    wod_notes: str | None = Field(None, max_length=2000)


# --- TABLA DE POSICIONES POR WOD (panel del coach) ---
class WodDaySummary(BaseModel):
    """Una fecha del grupo en la que hay un WOD prescrito (wod_format) — para que el coach
    elija cuál quiere ver en la tabla de posiciones por WOD."""
    scheduled_date: date
    wod_format: str
    # No se guarda aparte: es el nombre del ejercicio del bloque metabólico (ver
    # backend/routers/groups.py: get_group_wod_days) — mismo texto que el coach ya escribió
    # al armar la sesión.
    wod_name: Optional[str] = None
    time_cap_seconds: Optional[int] = None
    participants_count: int = 0


class WodLeaderboardRow(BaseModel):
    """Una fila de la tabla de posiciones de UN WOD específico: todos los atletas del grupo que
    lo tenían prescrito ese día, ordenados por su resultado según el formato (menor tiempo,
    más rondas/reps, más peso/calorías/distancia/vatios — ver _rank_wod_sessions). Los que
    todavía no lo completan aparecen al final, sin rank."""
    user_id: UUID
    full_name: str
    has_avatar: bool = False
    wod_format: str
    wod_name: Optional[str] = None  # ver WodDaySummary.wod_name
    score_label: Optional[str] = None
    rank: Optional[int] = None
    completed: bool = False
