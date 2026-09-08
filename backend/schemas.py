from typing import Annotated, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator
from datetime import datetime, date

from backend.sanitize import clean_text

Dia = Annotated[int, Field(ge=0, le=6)]  # 0 = Lunes ... 6 = Domingo


class SanitizedModel(BaseModel):
    """Base para esquemas de ENTRADA: sanea todo campo string (quita HTML/scripts, colapsa
    espacios, recorta) antes de que Pydantic valide los demás constraints. La contraseña se
    deja intacta (recortarla o limpiarla cambiaría lo que el usuario realmente escribió)."""

    @model_validator(mode="before")
    @classmethod
    def _sanitize_strings(cls, data):
        if isinstance(data, dict):
            return {
                key: (clean_text(value) if isinstance(value, str) and key != "password" else value)
                for key, value in data.items()
            }
        return data


class MessageResponse(BaseModel):
    message: str


# --- ESQUEMAS DE AUTENTICACIÓN ---
class UserRegister(SanitizedModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["athlete", "coach"] = "athlete"
    body_weight: float | None = Field(None, ge=0, le=500)

class UserLogin(SanitizedModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

# Actualizamos UserResponse para que también devuelva el rol al frontend
class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    body_weight: float | None = None
    role: str # ¡Agregamos el rol aquí!

    class Config:
        from_attributes = True


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

# --- ESQUEMAS PARA SESIONES Y SERIES (CORREGIDOS) ---
class SessionCreate(SanitizedModel):
    mesocycle_id: UUID
    scheduled_date: date

class AIGenerateRequest(SanitizedModel):
    mesocycle_id: UUID
    context: str = Field(..., min_length=1, max_length=2000)
    weeks_count: int = Field(..., ge=1, le=52)
    sessions_per_week: int = Field(..., ge=1, le=7)

class ExerciseResponse(BaseModel):
    id: UUID
    name: str
    category: Optional[str] = None

    class Config:
        from_attributes = True

class SetUpdate(SanitizedModel):
    exercise_name: str | None = Field(None, min_length=1, max_length=100)
    prescribed_reps: int = Field(..., ge=1, le=100)
    rpe: float | None = Field(None, ge=0, le=10)
    prescribed_weight: float | None = Field(None, ge=0, le=1000)

class SetCreate(SanitizedModel):
    exercise_name: str = Field(..., min_length=1, max_length=100)
    prescribed_reps: int = Field(..., ge=1, le=100)
    rpe: float | None = Field(None, ge=0, le=10)
    prescribed_weight: float | None = Field(None, ge=0, le=1000)

class SetLogUpdate(SanitizedModel):
    """Lo que el ATLETA reporta tras entrenar: lo que hizo de verdad, no lo prescrito."""
    actual_reps: int | None = Field(None, ge=0, le=200)
    actual_weight: float | None = Field(None, ge=0, le=1000)
    technique_feedback: str | None = Field(None, max_length=500)

class SetResponse(BaseModel):
    id: UUID
    set_order: int
    prescribed_reps: int
    rpe: Optional[int] = None
    prescribed_weight: float | None = None # <-- ¡ESTO FALTABA!
    actual_reps: Optional[int] = None
    actual_weight: Optional[float] = None
    technique_feedback: Optional[str] = None
    exercise: ExerciseResponse

    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: UUID
    mesocycle_id: UUID
    scheduled_date: date
    completed_date: Optional[datetime] = None
    athlete_notes: Optional[str] = None
    status: str
    parent_session_id: Optional[UUID] = None  # si no es None, es una versión adaptada de otra sesión
    duration_minutes: Optional[int] = None
    sets: List[SetResponse] = [] # ¡Aquí anidamos los sets!

    class Config:
        from_attributes = True

class MesocycleFullResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str | None = None # <-- Agregamos el nombre aquí también
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    sessions: List[SessionResponse] = [] # ¡Aquí anidamos las sesiones!

    class Config:
        from_attributes = True

class PRResponse(BaseModel):
    id: UUID
    exercise_name: str
    max_weight_kg: float
    last_updated: datetime

    class Config:
        from_attributes = True

# Esquema rápido para recibir la marca
class PRCreate(SanitizedModel):
    exercise_name: str = Field(..., min_length=1, max_length=100)
    max_weight_kg: float = Field(..., ge=0, le=1000)


class MesocycleManualCreate(SanitizedModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date
    weeks_count: int = Field(..., ge=1, le=52)
    training_days: List[Dia]  # 0 = Lunes, 1 = Martes ... 6 = Domingo

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
    members: List[GroupMemberResponse] = []

    class Config:
        from_attributes = True

class GroupSummaryResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    member_count: int
    coach_name: str | None = None  # solo relevante cuando lo consulta un admin


# --- ESQUEMAS PARA PROGRAMAR MESOCICLOS A UN GRUPO COMPLETO ---
class MesocycleManualGroupCreate(SanitizedModel):
    group_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    discipline: str = Field(..., min_length=1, max_length=50)
    start_date: date
    weeks_count: int = Field(..., ge=1, le=52)
    training_days: List[Dia]

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


class GroupSessionExerciseDelete(SanitizedModel):
    """Elimina por completo un ejercicio (todas sus series) de la sesión de una fecha dada,
    para TODOS los atletas del programa."""
    program_name: str = Field(..., min_length=1, max_length=100)
    program_start_date: date
    scheduled_date: date
    exercise_name: str = Field(..., min_length=1, max_length=100)


# --- ESQUEMAS PARA EL PANEL DE ADMINISTRACIÓN ---
class UserRoleUpdate(SanitizedModel):
    """Solo un admin puede cambiar el rol de un usuario (incluyendo promover a otro admin)."""
    role: Literal["athlete", "coach", "admin"]


class AdminOverview(BaseModel):
    total_users: int
    total_coaches: int
    total_athletes: int
    total_admins: int
    total_groups: int
    total_mesocycles: int
    total_sessions: int
    sessions_completed: int
    sessions_pending: int


# --- ESQUEMAS PARA EL CALCULADOR DE "FIT LEVEL" (halterofilia / gimnasia / metcon) ---
class FitnessBenchmarkUpdate(SanitizedModel):
    """Todos los campos son opcionales: el atleta llena solo las marcas que ya tiene."""
    body_weight: float | None = Field(None, ge=20, le=300)
    # Halterofilia (1RM en kg)
    snatch_kg: float | None = Field(None, ge=0, le=400)
    clean_jerk_kg: float | None = Field(None, ge=0, le=400)
    back_squat_kg: float | None = Field(None, ge=0, le=500)
    deadlift_kg: float | None = Field(None, ge=0, le=500)
    # Gimnasia (repeticiones máximas)
    pull_ups_max: int | None = Field(None, ge=0, le=200)
    push_ups_max: int | None = Field(None, ge=0, le=500)
    muscle_ups_max: int | None = Field(None, ge=0, le=100)
    hspu_max: int | None = Field(None, ge=0, le=200)
    # Metcon (tiempo en segundos, salvo Cindy que es AMRAP de repeticiones)
    fran_seconds: int | None = Field(None, ge=30, le=3600)
    grace_seconds: int | None = Field(None, ge=30, le=3600)
    cindy_total_reps: int | None = Field(None, ge=0, le=2000)
    row_2k_seconds: int | None = Field(None, ge=300, le=3600)


class FitnessLevelResponse(BaseModel):
    body_weight: float | None = None
    values: dict[str, float] = {}
    category_scores: dict[str, float] = {}
    category_levels: dict[str, str] = {}
    overall_score: float | None = None
    overall_level: str | None = None


# --- ESQUEMA PARA ADAPTAR UNA SESIÓN AL TIEMPO DISPONIBLE ---
class SessionAdaptRequest(SanitizedModel):
    available_minutes: int = Field(..., ge=10, le=180)
