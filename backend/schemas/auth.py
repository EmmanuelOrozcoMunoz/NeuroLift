from typing import Literal

from pydantic import EmailStr, Field

from backend.schemas.common import SanitizedModel


# --- ESQUEMAS DE AUTENTICACIÓN ---
class UserRegister(SanitizedModel):
    """Alta de un ATLETA. Dos caminos (ver routers/auth.py):
    - Autoregistro: sin sesión, con el código de invitación del box (`invite_code`).
    - Un coach/dueño ya autenticado registra a un atleta: el box sale de quien lo registra.
    Los coaches los da de alta el dueño del box (POST /boxes/me/coaches) y los dueños nacen al
    registrar su box (POST /boxes/register) — nadie puede autoasignarse esos roles aquí."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["athlete"] = "athlete"
    body_weight: float | None = Field(None, ge=0, le=500)
    invite_code: str | None = Field(None, max_length=16)


class UserLogin(SanitizedModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
