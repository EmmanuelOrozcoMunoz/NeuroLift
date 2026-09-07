from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional, List
from datetime import datetime
from datetime import date


# --- ESQUEMAS DE AUTENTICACIÓN ---
class UserRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "athlete" # Por defecto creamos atletas, a menos que se especifique coach
    body_weight: float | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

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
class MesocycleCreate(BaseModel):
    user_id: UUID
    name: str
    discipline: str
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
class SessionCreate(BaseModel):
    mesocycle_id: UUID
    scheduled_date: date

class AIGenerateRequest(BaseModel):
    mesocycle_id: UUID
    context: str
    weeks_count: int
    sessions_per_week: int

class ExerciseResponse(BaseModel):
    id: UUID
    name: str
    category: Optional[str] = None
    
    class Config:
        from_attributes = True

class SetUpdate(BaseModel):
    exercise_name: str | None = None
    prescribed_reps: int
    rpe: float | None = None
    prescribed_weight: float | None = None

class SetCreate(BaseModel):
    exercise_name: str
    prescribed_reps: int
    rpe: float | None = None
    prescribed_weight: float | None = None

class SetResponse(BaseModel):
    id: UUID
    set_order: int
    prescribed_reps: int
    rpe: Optional[int] = None
    prescribed_weight: float | None = None # <-- ¡ESTO FALTABA!
    exercise: ExerciseResponse
    
    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: UUID
    mesocycle_id: UUID
    scheduled_date: date
    athlete_notes: Optional[str] = None
    status: str
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
class PRCreate(BaseModel):
    exercise_name: str
    max_weight_kg: float


class MesocycleManualCreate(BaseModel):
    user_id: UUID
    name: str
    discipline: str
    start_date: date
    weeks_count: int
    training_days: List[int] # 0 = Lunes, 1 = Martes ... 6 = Domingo

class AIGenerateSmart(BaseModel):
    user_id: UUID
    name: str
    discipline: str
    start_date: date
    weeks_count: int
    training_days: List[int]
    context: str


# --- ESQUEMAS PARA GRUPOS DE ATLETAS ---
class GroupCreate(BaseModel):
    name: str
    athlete_ids: List[UUID] = []

class GroupMemberAdd(BaseModel):
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


# --- ESQUEMAS PARA PROGRAMAR MESOCICLOS A UN GRUPO COMPLETO ---
class MesocycleManualGroupCreate(BaseModel):
    group_id: UUID
    name: str
    discipline: str
    start_date: date
    weeks_count: int
    training_days: List[int]

class AIGenerateSmartGroup(BaseModel):
    group_id: UUID
    name: str
    discipline: str
    start_date: date
    weeks_count: int
    training_days: List[int]
    context: str


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


class GroupSessionExerciseAdd(BaseModel):
    """Añade el mismo ejercicio a la sesión de una fecha dada, para TODOS los atletas del programa."""
    program_name: str
    program_start_date: date
    scheduled_date: date
    exercise_name: str
    prescribed_sets: int = 3
    prescribed_reps: int
    rpe: float | None = None
    prescribed_weight: float | None = None


class GroupSessionExerciseUpdate(BaseModel):
    """Actualiza (nombre/series/reps/RPE/peso) un ejercicio ya existente en la sesión de una fecha
    dada, para TODOS los atletas del programa. Se identifica el ejercicio por su nombre ACTUAL;
    si se reduce el número de series se borran las sobrantes, si se aumenta se crean nuevas."""
    program_name: str
    program_start_date: date
    scheduled_date: date
    exercise_name: str
    new_exercise_name: str
    prescribed_sets: int
    prescribed_reps: int
    rpe: float | None = None
    prescribed_weight: float | None = None


class GroupSessionExerciseDelete(BaseModel):
    """Elimina por completo un ejercicio (todas sus series) de la sesión de una fecha dada,
    para TODOS los atletas del programa."""
    program_name: str
    program_start_date: date
    scheduled_date: date
    exercise_name: str

