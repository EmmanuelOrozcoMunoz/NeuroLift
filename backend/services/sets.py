"""Copia de series entre sesiones (grupos, planes adquiridos, clases registradas).

Antes cada sitio armaba `models.Set(...)` campo por campo, y cada columna nueva (como
`coach_note`) había que acordarse de agregarla en todos. Ahora la lista vive aquí y
`tests/test_set_copies.py` falla si alguien agrega una columna a `Set` sin decidir si se copia.
"""
from typing import NamedTuple

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


class FilaSerie(NamedTuple):
    """Una serie a crear: sus repeticiones y su carga (kg fijos o % de 1RM)."""
    reps: int
    weight: float | None
    percentage: float | None


def filas_de(req) -> list[FilaSerie]:
    """Las series que pide una petición de plan o de grupo. Con `series` (rampas) cada elemento es
    su propia serie; sin ella, `prescribed_sets` series iguales (el formato de siempre)."""
    if getattr(req, "series", None):
        return [FilaSerie(s.prescribed_reps, s.prescribed_weight, s.prescribed_percentage) for s in req.series]
    return [FilaSerie(req.prescribed_reps, req.prescribed_weight, req.prescribed_percentage)] * req.prescribed_sets


def reservar_orden(series_de_la_sesion: list[models.Set], ejercicio_id, cantidad: int = 1) -> int:
    """Primer `set_order` para `cantidad` series nuevas de un ejercicio. Si el ejercicio ya está en
    la sesión, justo después de su última serie (y las que venían después se corren `cantidad`
    posiciones): así quedan juntas en vez de aparecer como otra tarjeta del mismo ejercicio. Si es
    nuevo, al final (después del mayor orden, no del conteo: al borrar series quedan huecos)."""
    mismas = [s.set_order for s in series_de_la_sesion if s.exercise_id == ejercicio_id]
    if not mismas:
        return max((s.set_order for s in series_de_la_sesion), default=0) + 1
    despues_de = max(mismas)
    for otra in series_de_la_sesion:
        if otra.set_order > despues_de:
            otra.set_order += cantidad
    return despues_de + 1
