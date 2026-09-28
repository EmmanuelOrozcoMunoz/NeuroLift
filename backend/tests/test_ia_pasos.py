"""Pasos puros de la generación con IA (sin base de datos ni red)."""
from datetime import date

from backend.services.ai_mesocycles import (
    SEMANAS_POR_CHUNK,
    especificar_chunks,
    fechas_de_entrenamiento,
    guia_por_fecha,
    limpiar_ejercicio,
)


def test_fechas_solo_los_dias_de_entrenamiento():
    # lunes 2026-01-05, semanas 1 y 2, entrena lunes y jueves
    fechas = fechas_de_entrenamiento(date(2026, 1, 5), 2, [0, 3])
    assert fechas == ["2026-01-05", "2026-01-08", "2026-01-12", "2026-01-15"]


def test_chunks_de_tres_semanas_con_sus_fechas():
    fechas = fechas_de_entrenamiento(date(2026, 1, 5), 7, [0, 3])
    specs = especificar_chunks(fechas, 7, 2, None)
    assert [(s[0], s[1], len(s[2])) for s in specs] == [(1, 3, 6), (4, 6, 6), (7, 7, 2)]
    assert SEMANAS_POR_CHUNK == 3 and all(s[3] == "" for s in specs)


def test_la_guia_se_ata_a_la_fecha_y_omite_dias_sin_guia():
    fechas = ["2026-01-05", "2026-01-08"]  # lunes y jueves
    texto = guia_por_fecha(fechas, {0: "Piernas"})
    assert "2026-01-05 (Lunes): Piernas" in texto and "2026-01-08" not in texto
    assert guia_por_fecha(fechas, None) == "" and guia_por_fecha(fechas, {2: "Nada"}) == ""


def test_limpiar_ejercicio_con_porcentaje_usa_la_marca_actual():
    ej = limpiar_ejercicio({"exercise_name": "Back Squat", "prescribed_percentage": "80", "prescribed_sets": 3}, {"back squat": 100})
    assert (ej.series, ej.porcentaje, ej.peso, ej.referencia) == (3, 80.0, 80, "Back Squat")


def test_limpiar_ejercicio_kg_fijo_que_coincide_con_marca_deriva_el_porcentaje():
    ej = limpiar_ejercicio({"exercise_name": "Deadlift", "weight_kg": 120}, {"deadlift": 150})
    assert (ej.peso, ej.porcentaje, ej.referencia) == (120.0, 80, "Deadlift")


def test_limpiar_ejercicio_descarta_valores_invalidos_y_usa_defaults():
    ej = limpiar_ejercicio({"prescribed_weight": "mucho", "prescribed_percentage": "n/a", "rpe": "7.9", "block": "raro"}, {})
    assert (ej.nombre, ej.series, ej.reps, ej.rpe) == ("Ejercicio Desconocido", 1, 1, 7)
    assert (ej.peso, ej.porcentaje, ej.referencia, ej.bloque) == (None, None, None, None)
