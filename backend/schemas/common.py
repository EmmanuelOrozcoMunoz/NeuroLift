from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from backend.sanitize import clean_text

Dia = Annotated[int, Field(ge=0, le=6)]  # 0 = Lunes ... 6 = Domingo

# Parte de la sesión a la que pertenece un ejercicio. "warmup"/"strength"/"accessory" sirven
# para cualquier disciplina; "weightlifting"/"skills"/"metcon" son específicos de CrossFit;
# "main" es un cajón genérico para disciplinas que no necesitan más desglose que
# calentamiento + entrenamiento principal. None = sin bloque asignado.
Bloque = Literal["warmup", "strength", "weightlifting", "skills", "metcon", "accessory", "main"]

# Formatos estándar de WOD de CrossFit que el coach puede prescribir para una sesión.
FormatoWod = Literal["for_time", "amrap", "amrap_reps", "emom", "tabata", "1rm", "calories", "distance", "watts"]


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
