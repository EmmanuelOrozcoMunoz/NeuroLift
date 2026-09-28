"""Copia de series entre sesiones (grupos, planes adquiridos, clases registradas).

Antes cada sitio armaba `models.Set(...)` campo por campo, y cada columna nueva (como
`coach_note`) había que acordarse de agregarla en todos. Ahora la lista vive aquí y
`tests/test_set_copies.py` falla si alguien agrega una columna a `Set` sin decidir si se copia.
"""
from backend import models

# Lo que el coach PRESCRIBE: viaja en toda copia.
CAMPOS_PRESCRITOS = (
    "exercise_id",
    "set_order",
    "block",
    "prescribed_reps",
    "prescribed_weight",
    "prescribed_percentage",
    "reference_exercise",
    "rpe",
    "coach_note",
)

# Lo que es propio de cada copia (identidad, dueño y lo que el atleta registra al entrenar):
# nunca se copia.
CAMPOS_NO_COPIADOS = (
    "id",
    "session_id",
    "actual_reps",
    "actual_weight",
    "video_url",
    "technique_score",
    "technique_feedback",
    "is_pr_attempt",
)

_IGUAL = object()


def clonar_set(origen: models.Set, session_id, *, prescribed_weight=_IGUAL) -> models.Set:
    """Devuelve una serie nueva (sin agregar a la sesión de BD) con lo prescrito por `origen`.

    `prescribed_weight` reemplaza la carga cuando se resuelve por atleta (% de 1RM -> kg); si
    no se pasa, se copia tal cual. Pasar `None` es válido y significa "sin carga"."""
    datos = {campo: getattr(origen, campo) for campo in CAMPOS_PRESCRITOS}
    if prescribed_weight is not _IGUAL:
        datos["prescribed_weight"] = prescribed_weight
    return models.Set(session_id=session_id, **datos)
