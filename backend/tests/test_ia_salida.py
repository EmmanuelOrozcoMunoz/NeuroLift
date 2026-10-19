"""La limpieza de lo que devuelve la IA (backend/services/ai_salida.py): pura, sin base ni red."""
from datetime import date

import pytest

from backend.services.ai_salida import (
    FORMATOS_CON_TIEMPO,
    FORMATOS_DE_WOD,
    MAX_EJERCICIOS_POR_SESION,
    MAX_REPS,
    MAX_SERIES,
    a_entero,
    emparejar_fechas,
    fecha_de_texto,
    limpiar_ejercicio,
    limpiar_sesion,
    nombre_canonico,
    orden_de_bloques_limpio,
    sesiones_de_respuesta,
    wod_limpio,
)

MARCAS = {"back squat": 100.0, "snatch": 80.0}


# ------------------------------------------------------------------ nombres

@pytest.mark.parametrize("escrito, esperado", [
    ("Back Squat", "Back Squat"),
    ("back squat", "Back Squat"),
    ("Sentadilla trasera", "Back Squat"),
    ("clean and jerk", "Clean & Jerk"),
    ("Dos tiempos", "Clean & Jerk"),
    ("arranque", "Snatch"),
    ("Push-up", "Push-up"),            # lo que no es un levantamiento conocido se respeta
    ("  Dumbbell   Row ", "Dumbbell Row"),
])
def test_los_levantamientos_se_guardan_con_su_nombre_canonico(escrito, esperado):
    assert nombre_canonico(escrito) == esperado


def test_un_nombre_que_no_es_texto_no_es_un_nombre():
    assert nombre_canonico(None) is None and nombre_canonico(5) is None and nombre_canonico("   ") is None


# ------------------------------------------------------------------ cargas

def test_con_marca_el_porcentaje_se_resuelve_a_kg_y_se_conserva():
    ej = limpiar_ejercicio({"exercise_name": "Back Squat", "prescribed_sets": 3, "prescribed_reps": 5,
                            "prescribed_percentage": 80, "block": "strength"}, MARCAS)
    assert (ej.series, ej.reps, ej.peso, ej.porcentaje, ej.referencia, ej.bloque) == (3, 5, 80, 80, "Back Squat", "strength")
    assert ej.advertencias == []


def test_un_kg_inventado_para_un_levantamiento_sin_marca_se_descarta_y_se_avisa():
    ej = limpiar_ejercicio({"exercise_name": "Snatch", "prescribed_reps": 2, "prescribed_weight": 60}, {})
    assert (ej.peso, ej.porcentaje, ej.referencia) == (None, None, None)
    assert any("sin que haya marca" in a for a in ej.advertencias)


def test_un_kg_para_un_levantamiento_derivado_sin_marca_propia_tambien_se_descarta():
    # hay marca de Back Squat pero no de Front Squat: sin % no hay cómo respaldar ese kg
    ej = limpiar_ejercicio({"exercise_name": "Front Squat", "prescribed_reps": 5, "prescribed_weight": 80}, MARCAS)
    assert ej.peso is None and ej.advertencias


def test_un_kg_para_un_accesorio_se_respeta():
    ej = limpiar_ejercicio({"exercise_name": "Dumbbell Row", "prescribed_sets": 3, "prescribed_reps": 10, "prescribed_weight": 22.5}, {})
    assert (ej.peso, ej.porcentaje, ej.advertencias) == (22.5, None, [])


def test_un_porcentaje_sin_marca_queda_sin_kg_y_se_avisa():
    ej = limpiar_ejercicio({"exercise_name": "Snatch", "prescribed_reps": 2, "prescribed_percentage": 70}, {"back squat": 100})
    assert (ej.peso, ej.porcentaje, ej.referencia) == (None, 70.0, "Snatch")
    assert any("sin marca de Snatch" in a for a in ej.advertencias)


def test_en_una_plantilla_no_hay_atleta_los_porcentajes_se_conservan_sin_avisos_y_ningun_kg_de_barra():
    pct = limpiar_ejercicio({"exercise_name": "Back Squat", "prescribed_reps": 5, "prescribed_percentage": 75}, None)
    assert (pct.peso, pct.porcentaje, pct.referencia, pct.advertencias) == (None, 75.0, "Back Squat", [])
    kg = limpiar_ejercicio({"exercise_name": "Back Squat", "prescribed_reps": 5, "prescribed_weight": 100}, None)
    assert kg.peso is None and kg.advertencias


@pytest.mark.parametrize("valor", [500, 121, 0, -5, "mucho", None])
def test_un_porcentaje_fuera_de_rango_se_descarta(valor):
    ej = limpiar_ejercicio({"exercise_name": "Back Squat", "prescribed_reps": 5, "prescribed_percentage": valor}, MARCAS)
    assert ej.porcentaje is None and ej.peso is None
    if isinstance(valor, int) and valor > 120:
        assert any("fuera de rango" in a for a in ej.advertencias)


def test_series_y_repeticiones_absurdas_se_recortan_no_se_ignoran():
    ej = limpiar_ejercicio({"exercise_name": "Burpee", "prescribed_sets": 500, "prescribed_reps": 9999}, {})
    assert (ej.series, ej.reps) == (MAX_SERIES, MAX_REPS)
    assert len(ej.filas_a_guardar()) == MAX_SERIES


@pytest.mark.parametrize("sets, reps, esperado", [(0, 0, (1, 1)), ("3", "8", (3, 8)), ("x", None, (1, 1)), (-2, -2, (1, 1)), (2.9, 4.2, (2, 4))])
def test_series_y_repeticiones_invalidas_usan_el_valor_por_defecto(sets, reps, esperado):
    ej = limpiar_ejercicio({"exercise_name": "Push-up", "prescribed_sets": sets, "prescribed_reps": reps}, {})
    assert (ej.series, ej.reps) == esperado


@pytest.mark.parametrize("rpe, esperado", [(8, 8), ("7.9", 7), (0, None), (11, None), ("mucho", None), (None, None)])
def test_el_rpe_fuera_de_1_a_10_no_se_inventa(rpe, esperado):
    assert limpiar_ejercicio({"exercise_name": "Push-up", "rpe_target": rpe}, {}).rpe == esperado


def test_a_entero_no_se_rompe_con_basura():
    for basura in (float("nan"), float("inf"), "inf", True, [], {}):
        assert a_entero(basura, 1, 10) is None
    assert a_entero(5, 1, 10) == 5 and a_entero(50, 1, 10) is None and a_entero(50, 1, 10, acotar=True) == 10


# ------------------------------------------------------------------ rampas y notas

def test_una_rampa_son_series_distintas_cada_una_con_su_carga():
    ej = limpiar_ejercicio({"exercise_name": "Snatch", "block": "weightlifting", "prescribed_sets": 4, "prescribed_reps": 3, "series": [
        {"prescribed_reps": 3, "prescribed_percentage": 50}, {"prescribed_reps": 3, "prescribed_percentage": 60},
        {"prescribed_reps": 1, "prescribed_percentage": 70}, {"prescribed_reps": 1, "prescribed_percentage": 80},
    ]}, MARCAS)
    assert ej.series == 4 and [(f.reps, f.porcentaje, f.peso) for f in ej.filas] == [(3, 50, 40), (3, 60, 47.5), (1, 70, 55), (1, 80, 65)]
    assert (ej.reps, ej.porcentaje, ej.referencia) == (3, 50.0, "Snatch")
    assert ej.filas_a_guardar() == ej.filas


def test_una_rampa_de_una_sola_serie_es_un_ejercicio_normal():
    ej = limpiar_ejercicio({"exercise_name": "Back Squat", "prescribed_sets": 5, "series": [{"prescribed_reps": 4, "prescribed_percentage": 90}]}, MARCAS)
    assert ej.filas is None and (ej.series, ej.reps, ej.porcentaje, ej.peso) == (1, 4, 90.0, 90)


def test_una_rampa_se_recorta_ignora_filas_rotas_y_resuelve_cada_carga():
    filas = [{"prescribed_reps": 5, "prescribed_percentage": 50 + i} for i in range(30)] + ["basura", None]
    ej = limpiar_ejercicio({"exercise_name": "Back Squat", "series": filas}, MARCAS)
    assert len(ej.filas) == MAX_SERIES
    # una fila con porcentaje absurdo no tumba el resto
    ej = limpiar_ejercicio({"exercise_name": "Back Squat", "series": [
        {"prescribed_reps": 5, "prescribed_percentage": 70}, {"prescribed_reps": 5, "prescribed_percentage": 900}]}, MARCAS)
    assert [f.porcentaje for f in ej.filas] == [70.0, None]


def test_la_nota_del_coach_por_ejercicio_conserva_sus_lineas_y_quita_html():
    ej = limpiar_ejercicio({"exercise_name": "Back Squat", "coach_note": "  Codos arriba\n<b>Pausa</b> abajo  "}, MARCAS)
    assert ej.nota == "Codos arriba\nPausa abajo"
    assert limpiar_ejercicio({"exercise_name": "Back Squat", "coach_note": "x" * 900}, MARCAS).nota == "x" * 300
    assert limpiar_ejercicio({"exercise_name": "Back Squat", "coach_note": "  "}, MARCAS).nota is None
    assert limpiar_ejercicio({"exercise_name": "Back Squat", "coach_note": 5}, MARCAS).nota is None


def test_lo_que_ya_funcionaba_sigue_igual_valores_raros_y_derivar_el_porcentaje():
    ej = limpiar_ejercicio({"exercise_name": "Deadlift", "weight_kg": 120}, {"deadlift": 150})
    assert (ej.peso, ej.porcentaje, ej.referencia) == (120.0, 80, "Deadlift")
    ej = limpiar_ejercicio({"prescribed_weight": "mucho", "prescribed_percentage": "n/a", "rpe": "7.9", "block": "raro"}, {})
    assert (ej.nombre, ej.series, ej.reps, ej.rpe, ej.peso, ej.porcentaje, ej.referencia, ej.bloque) == (
        "Ejercicio Desconocido", 1, 1, 7, None, None, None, None)


# ------------------------------------------------------------------ WOD

@pytest.mark.parametrize("formato", FORMATOS_DE_WOD)
def test_los_nueve_formatos_de_wod_se_aceptan(formato):
    wod = wod_limpio({"name": "X", "format": formato, "time_cap_minutes": 12, "description": "descripción"})
    assert wod["format"] == formato
    assert wod["time_cap_seconds"] == (720 if formato in FORMATOS_CON_TIEMPO else None)


def test_el_wod_conserva_las_lineas_de_la_descripcion_y_quita_html():
    wod = wod_limpio({"name": " Fran ", "format": "for_time", "time_cap_minutes": 10,
                      "description": "21-15-9\nThrusters\n\n\nPull-ups <b>estrictos</b>"})
    assert wod["notes"] == "Fran\n21-15-9\nThrusters\n\nPull-ups estrictos"


# ------------------------------------------------------------------ sesiones

def test_una_sesion_trae_calentamiento_en_texto_notas_y_orden_de_bloques():
    sesion = limpiar_sesion({
        "athlete_notes": "Semana de volumen\nfocus en técnica",
        "warmup_notes": "5 min de remo\n\n\n3 aproximaciones al primer set",
        "block_order": ["warmup", "skills", "strength", "inventado", "strength"],
        "wod": {"name": "Cindy", "format": "amrap", "time_cap_minutes": 20, "description": "5-10-15"},
        "exercises": [
            {"exercise_name": "Back Squat", "block": "strength", "prescribed_sets": 3, "prescribed_reps": 5},
            {"exercise_name": "Pull-ups", "block": "skills", "prescribed_sets": 3, "prescribed_reps": 8},
        ],
    }, date(2026, 1, 5), MARCAS)
    assert sesion.fecha == date(2026, 1, 5)
    assert sesion.notas_atleta == "Semana de volumen\nfocus en técnica"
    assert sesion.calentamiento == "5 min de remo\n\n3 aproximaciones al primer set"
    assert sesion.orden_de_bloques == "warmup,skills,strength"   # sin el bloque inventado ni repetidos
    assert sesion.wod["format"] == "amrap" and len(sesion.ejercicios) == 2


def test_el_orden_de_bloques_solo_cuenta_si_hay_algo_que_ordenar():
    presentes = {"warmup", "strength", "metcon"}
    assert orden_de_bloques_limpio("metcon, strength", presentes) == "metcon,strength"
    assert orden_de_bloques_limpio(["strength"], presentes) is None                  # uno solo: nada que ordenar
    assert orden_de_bloques_limpio(["skills", "weightlifting"], presentes) is None   # bloques que no están en la sesión
    assert orden_de_bloques_limpio(None, presentes) is None and orden_de_bloques_limpio(5, presentes) is None


def test_un_ejercicio_roto_se_descarta_con_aviso_sin_tumbar_la_sesion():
    sesion = limpiar_sesion({"exercises": [
        "basura", None, 5, {"exercise_name": "Back Squat", "prescribed_reps": 5}, {"exercise_name": ["lista"], "series": "x"},
    ]}, date(2026, 1, 5), {})
    assert [e.nombre for e in sesion.ejercicios] == ["Back Squat", "Ejercicio Desconocido"]
    assert sum("no tenía el formato esperado" in a for a in sesion.advertencias) == 3


def test_una_sesion_con_demasiados_ejercicios_se_recorta():
    sesion = limpiar_sesion({"exercises": [{"exercise_name": f"Ej {i}", "prescribed_reps": 5} for i in range(80)]}, date(2026, 1, 5), {})
    assert len(sesion.ejercicios) == MAX_EJERCICIOS_POR_SESION


def test_una_sesion_vacia_o_sin_formato_no_rompe():
    for rota in ({}, {"exercises": None}, {"exercises": "texto"}, {"wod": "texto", "warmup_notes": 5, "athlete_notes": None}):
        sesion = limpiar_sesion(rota, date(2026, 1, 5), {})
        assert (sesion.ejercicios, sesion.calentamiento, sesion.wod, sesion.orden_de_bloques, sesion.notas_atleta) == ([], None, None, None, "")


# ------------------------------------------------------------------ fechas

def _s(fecha, **extra):
    return {"scheduled_date": fecha, "exercises": [], **extra}


def test_sesiones_de_respuesta_aplana_las_semanas_y_tolera_basura():
    respuesta = {"weeks": [{"sessions": [_s("2026-01-05"), "basura", None]}, {"sessions": [_s("2026-01-08")]}, "x", {"sessions": 5}]}
    assert [s["scheduled_date"] for s in sesiones_de_respuesta(respuesta)] == ["2026-01-05", "2026-01-08"]
    assert sesiones_de_respuesta({"sessions": [_s("2026-01-05")]})[0]["scheduled_date"] == "2026-01-05"
    for nada in (None, [], "texto", {}, {"weeks": "x"}, {"error": "caído"}):
        assert sesiones_de_respuesta(nada) == []


def test_fecha_de_texto():
    assert fecha_de_texto(" 2026-01-05 ") == "2026-01-05"
    for mala in ("2026-13-45", "5 de enero", "", None, 20260105, "2026-1-5x"):
        assert fecha_de_texto(mala) is None


def test_las_fechas_pedidas_se_respetan_y_salen_en_orden():
    pares, faltantes = emparejar_fechas([_s("2026-01-08"), _s("2026-01-05")], ["2026-01-05", "2026-01-08"])
    assert [f for f, _ in pares] == ["2026-01-05", "2026-01-08"] and faltantes == []


def test_una_fecha_inventada_se_reasigna_a_la_fecha_libre_en_orden():
    esperadas = ["2026-01-05", "2026-01-07", "2026-01-09"]
    pares, faltantes = emparejar_fechas([_s("2026-01-05"), _s("1999-01-01"), _s("no es fecha")], esperadas)
    assert [f for f, _ in pares] == esperadas and faltantes == []


def test_una_fecha_repetida_ocupa_la_siguiente_libre_y_lo_que_sobra_se_descarta():
    pares, faltantes = emparejar_fechas([_s("2026-01-05", n=1), _s("2026-01-05", n=2), _s("2026-01-05", n=3)], ["2026-01-05", "2026-01-07"])
    assert [(f, s["n"]) for f, s in pares] == [("2026-01-05", 1), ("2026-01-07", 2)] and faltantes == []


def test_las_fechas_sin_sesion_se_reportan_como_faltantes():
    pares, faltantes = emparejar_fechas([_s("2026-01-05")], ["2026-01-05", "2026-01-07", "2026-01-09"])
    assert [f for f, _ in pares] == ["2026-01-05"] and faltantes == ["2026-01-07", "2026-01-09"]
    assert emparejar_fechas([], ["2026-01-05"]) == ([], ["2026-01-05"])
