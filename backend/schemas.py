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
        orm_mode = True

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

# --- ESQUEMAS PARA SESIONES ---
class SessionCreate(BaseModel):
    mesocycle_id: UUID
    scheduled_date: date

class SessionResponse(BaseModel):
    id: UUID
    mesocycle_id: UUID
    scheduled_date: date
    status: str

    class Config:
        from_attributes = True

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

class SetResponse(BaseModel):
    id: UUID
    set_order: int
    prescribed_reps: int
    rpe: Optional[int] = None
    exercise: ExerciseResponse # ¡Aquí anidamos el ejercicio!
    
    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: UUID
    scheduled_date: date
    athlete_notes: Optional[str] = None
    status: str
    sets: List[SetResponse] = [] # ¡Aquí anidamos los sets!
    
    class Config:
        from_attributes = True

class MesocycleFullResponse(BaseModel):
    id: UUID
    user_id: UUID
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
        orm_mode = True