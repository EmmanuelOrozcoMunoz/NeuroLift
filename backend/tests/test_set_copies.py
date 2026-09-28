"""Copiar series: cada columna de `Set` tiene que estar decidida (se copia o no se copia)."""
import uuid

from backend import models
from backend.services.sets import CAMPOS_NO_COPIADOS, CAMPOS_PRESCRITOS, clonar_set


def test_toda_columna_de_set_esta_clasificada():
    """Si agregas una columna a `Set` (como pasó con coach_note), este test falla hasta que la
    pongas en CAMPOS_PRESCRITOS (viaja en las copias) o en CAMPOS_NO_COPIADOS (es de cada copia)."""
    columnas = set(models.Set.__table__.columns.keys())
    clasificadas = set(CAMPOS_PRESCRITOS) | set(CAMPOS_NO_COPIADOS)
    assert columnas - clasificadas == set(), f"Columnas sin decidir: {sorted(columnas - clasificadas)}"
    assert clasificadas - columnas == set(), f"Campos que ya no existen: {sorted(clasificadas - columnas)}"
    assert not set(CAMPOS_PRESCRITOS) & set(CAMPOS_NO_COPIADOS)


def _serie_original():
    return models.Set(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        exercise_id=uuid.uuid4(),
        set_order=3,
        block="fuerza",
        prescribed_reps=5,
        prescribed_weight=80.0,
        prescribed_percentage=75.0,
        reference_exercise="Back Squat",
        rpe=8,
        coach_note="Codos arriba",
        actual_reps=5,
        actual_weight=82.5,
        video_url="video.mp4",
        technique_score=9.0,
        technique_feedback="Bien",
        is_pr_attempt=True,
    )


def test_clonar_copia_lo_prescrito_incluida_la_nota():
    origen = _serie_original()
    destino_sesion = uuid.uuid4()
    copia = clonar_set(origen, destino_sesion)
    assert copia.session_id == destino_sesion
    for campo in CAMPOS_PRESCRITOS:
        assert getattr(copia, campo) == getattr(origen, campo), campo
    assert copia.coach_note == "Codos arriba"


def test_clonar_no_copia_lo_que_registro_el_atleta():
    copia = clonar_set(_serie_original(), uuid.uuid4())
    assert copia.id is None  # la BD le asigna uno propio
    assert copia.actual_reps is None and copia.actual_weight is None
    assert copia.video_url is None and copia.technique_score is None and copia.technique_feedback is None
    assert not copia.is_pr_attempt


def test_clonar_puede_reemplazar_la_carga_incluso_con_none():
    origen = _serie_original()
    assert clonar_set(origen, uuid.uuid4(), prescribed_weight=62.5).prescribed_weight == 62.5
    assert clonar_set(origen, uuid.uuid4(), prescribed_weight=None).prescribed_weight is None
    assert clonar_set(origen, uuid.uuid4()).prescribed_weight == 80.0
