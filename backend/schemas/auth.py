from typing import Literal

from pydantic import EmailStr, Field

from backend.schemas.common import SanitizedModel


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
