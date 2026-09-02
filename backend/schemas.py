from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional, List
from datetime import datetime
from datetime import date


# Lo que esperamos recibir del front-end
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    body_weight: float | None = None

# Lo que la API le responde al front-end
class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    body_weight: float | None = None  # ¡Agregamos el peso aquí también!

    # Esto le permite a FastAPI convertir el objeto de la base de datos a JSON
    class Config:
        from_attributes = True
# --- ESQUEMAS DE AUTENTICACIÓN ---
class UserRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "athlete" # Por defecto creamos atletas, a menos que se especifique coach

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
