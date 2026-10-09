from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from backend.sanitize import clean_multiline, clean_text

Dia = Annotated[int, Field(ge=0, le=6)]  # 0 = Lunes ... 6 = Domingo

# Parte de la sesión a la que pertenece un ejercicio. "warmup"/"strength"/"accessory" sirven
# para cualquier disciplina; "weightlifting"/"skills"/"metcon" son específicos de CrossFit;
# "main" es un cajón genérico para disciplinas que no necesitan más desglose que
# calentamiento + entrenamiento principal. None = sin bloque asignado.
Bloque = Literal["warmup", "strength", "weightlifting", "skills", "metcon", "accessory", "main"]

# Formatos estándar de WOD de CrossFit que el coach puede prescribir para una sesión.
FormatoWod = Literal["for_time", "amrap", "amrap_reps", "emom", "tabata", "1rm", "calories", "distance", "watts"]


# Campos donde alguien escribe TEXTO LARGO en varias líneas (un WOD, el calentamiento, una nota,
# una descripción): conservan sus saltos de línea. Todo lo demás es de una sola línea (nombres,
# correos, títulos) y se colapsa a una línea. Se identifican por el nombre del campo, igual que
# la contraseña, para que cada esquema nuevo con uno de estos nombres quede bien sin acordarse.
CAMPOS_DE_TEXTO_LARGO = frozenset({"wod_notes", "warmup_notes", "coach_note", "athlete_notes", "description"})


class SanitizedModel(BaseModel):
    """Base para esquemas de ENTRADA: sanea todo campo string (quita HTML/scripts, recorta y
    colapsa espacios) antes de que Pydantic valide los demás constraints. Los campos de texto
    largo (CAMPOS_DE_TEXTO_LARGO) conservan sus saltos de línea; el resto se colapsa a una sola
    línea. La contraseña se deja intacta (recortarla o limpiarla cambiaría lo que el usuario
    realmente escribió)."""

    @model_validator(mode="before")
    @classmethod
    def _sanitize_strings(cls, data):
        if isinstance(data, dict):
            def limpiar(key, value):
                if not isinstance(value, str) or key == "password":
                    return value
                return clean_multiline(value) if key in CAMPOS_DE_TEXTO_LARGO else clean_text(value)

            return {key: limpiar(key, value) for key, value in data.items()}
        return data


class MessageResponse(BaseModel):
    message: str


class SerieDeEjercicio(SanitizedModel):
    """Una serie de un ejercicio con sus propias repeticiones y su propia carga (kg fijos O % de
    1RM). Una lista de estas permite rampas como 50 %x3, 60 %x3, 70 %x1, 80 %x1."""
    prescribed_reps: int = Field(..., ge=1, le=100)
    prescribed_weight: float | None = Field(None, ge=0, le=1000)
    prescribed_percentage: float | None = Field(None, ge=1, le=150)
