from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional
from datetime import datetime
from datetime import date

# Lo que esperamos recibir del front-end
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    bodyweight: Optional[float] = None

# Lo que la API le responde al front-end
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    bodyweight: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True

# --- ESQUEMAS PARA MESOCICLOS ---
class MesocycleCreate(BaseModel):
    user_id: UUID
    name: str
    discipline: str
    start_date: date
    end_date: Optional[date] = None
    ai_prompt_context: Optional[str] = None # Aquí la IA guardará el contexto del bloque

class MesocycleResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    discipline: str
    start_date: date
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