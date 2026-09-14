from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel

from backend.schemas.common import SanitizedModel


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


class AuditLogResponse(BaseModel):
    id: UUID
    created_at: Optional[datetime]
    level: str
    message: str

    class Config:
        from_attributes = True
