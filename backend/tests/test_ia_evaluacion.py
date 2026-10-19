"""Las reglas de evaluación de lo que devuelve la IA (backend/services/ai_evaluacion.py): una respuesta
buena no genera hallazgos y cada defecto genera EL suyo. Sin base ni red."""
import copy
import json

import pytest

from backend.services.ai_evaluacion import (
    Hallazgo,
    evaluar_respuesta,
    resumen,
    uso_de_componentes,
)

# Cuatro semanas, lunes y miércoles
FECHAS = ["2026-01-05", "2026-01-07", "2026-01-12", "2026-01-14", "2026-01-19", "2026-01-21", "2026-01-26", "2026-01-28"]
MARCAS = {"back squat": 100.0, "snatch": 70.0}


def _sesion(fecha, porcentaje=75, **extra):
    return {
        "scheduled_date": fecha,
        "athlete_notes": "ok",
        "warmup_notes": "5 min de remo\n3 aproximaciones",
        "block_order": None,
        "wod": {"name": "AMRAP 10", "format": "amrap", "time_cap_minutes": 10, "description": "5 pull-ups\n10 push-ups"},
        "exercises": [
            {"exercise_name": "Back Squat", "block": "strength", "prescribed_sets": 4, "prescribed_reps": 5, "rpe_target": 8,
             "prescribed_weight": None, "prescribed_percentage": porcentaje, "reference_exercise": "Back Squat",
             "coach_note": "Codos arriba", "series": None},
        ],
        **extra,
    }


def buena():
    """Cuatro semanas con la intensidad subiendo 70, 75, 80, 85 %."""
    semanas = []
    for i in range(4):
        semanas.append({"week_number": i + 1, "sessions": [_sesion(FECHAS[2 * i], 70 + 5 * i), _sesion(FECHAS[2 * i + 1], 70 + 5 * i)]})
    return {"mesocycle_focus": "fuerza", "weeks": semanas}


def evaluar(respuesta, **kw):
    kw.setdefault("fechas", FECHAS)
    kw.setdefault("prs", MARCAS)
    kw.setdefault("disciplina", "CrossFit")
    return evaluar_respuesta(respuesta, **kw)


def reglas(hallazgos):
    return sorted({h.regla for h in hallazgos})


def _sesiones(respuesta):
    return [s for semana in respuesta["weeks"] for s in semana["sessions"]]


def test_una_respuesta_buena_no_tiene_hallazgos():
    assert evaluar(buena()) == []
    assert resumen([]) == {"errores": 0, "avisos": 0}


# ------------------------------------------------------------------ cobertura de fechas

def test_una_fecha_sin_sesion_es_un_error():
    r = buena()
    r["weeks"][3]["sessions"].pop()
    hallazgos = evaluar(r)
    assert [(h.nivel, h.regla) for h in hallazgos if h.regla == "sin_sesion"] == [("error", "sin_sesion")]
    assert "2026-01-28" in hallazgos[0].detalle


def test_fecha_inventada_repetida_e_ilegible_son_avisos():
    r = buena()
    _sesiones(r)[0]["scheduled_date"] = "1999-12-31"        # inventada (y deja a 2026-01-05 sin sesión)
    _sesiones(r)[1]["scheduled_date"] = _sesiones(r)[2]["scheduled_date"]   # repetida
    _sesiones(r)[3]["scheduled_date"] = "pasado mañana"      # ilegible
    assert {"fecha_inventada", "fecha_repetida", "fecha_ilegible", "sin_sesion"} <= set(reglas(evaluar(r)))


# ------------------------------------------------------------------ bloques y WOD

def test_un_bloque_inventado_es_un_aviso_y_main_en_crossfit_tambien():
    r = buena()
    _sesiones(r)[0]["exercises"][0]["block"] = "inventado"
    _sesiones(r)[1]["exercises"][0]["block"] = "main"
    assert reglas(evaluar(r)) == ["bloque_generico", "bloque_invalido"]


def test_fuera_de_crossfit_no_se_esperan_metcon_ni_weightlifting():
    r = buena()
    _sesiones(r)[0]["exercises"][0]["block"] = "weightlifting"
    assert reglas(evaluar(r, disciplina="Powerlifting")) == ["bloque_ajeno_a_la_disciplina"]
    assert evaluar(r, disciplina="CrossFit") == []


def test_un_wod_con_formato_inventado_o_sin_duracion_es_un_aviso():
    r = buena()
    _sesiones(r)[0]["wod"] = {"name": "X", "format": "inventado", "time_cap_minutes": 10, "description": "algo"}
    _sesiones(r)[1]["wod"] = {"name": "Y", "format": "amrap", "time_cap_minutes": None, "description": "algo"}
    assert reglas(evaluar(r)) == ["wod_invalido", "wod_sin_tiempo"]


# ------------------------------------------------------------------ cargas

def test_un_kg_sin_marca_en_un_levantamiento_es_un_error_de_seguridad():
    r = buena()
    ej = _sesiones(r)[0]["exercises"][0]
    ej.update({"exercise_name": "Front Squat", "reference_exercise": None, "prescribed_percentage": None, "prescribed_weight": 85})
    hallazgos = evaluar(r)
    assert [(h.nivel, h.regla) for h in hallazgos] == [("error", "kg_inventado")]


def test_un_kg_fijo_habiendo_marca_es_un_aviso_y_un_accesorio_con_kg_no_es_nada():
    r = buena()
    _sesiones(r)[0]["exercises"][0].update({"prescribed_percentage": None, "prescribed_weight": 85})
    assert [(h.nivel, h.regla) for h in evaluar(r)] == [("aviso", "kg_con_marca")]
    r = buena()
    _sesiones(r)[0]["exercises"].append({"exercise_name": "Dumbbell Row", "block": "accessory", "prescribed_sets": 3,
                                         "prescribed_reps": 10, "prescribed_weight": 22.5})
    assert evaluar(r) == []


def test_porcentajes_altos_absurdos_y_sin_marca():
    r = buena()
    _sesiones(r)[0]["exercises"][0]["prescribed_percentage"] = 105
    _sesiones(r)[1]["exercises"][0]["prescribed_percentage"] = 300
    _sesiones(r)[2]["exercises"][0].update({"exercise_name": "Power Clean", "reference_exercise": "Power Clean"})
    resultado = {(h.nivel, h.regla) for h in evaluar(r)}
    assert {("aviso", "porcentaje_alto"), ("error", "porcentaje_absurdo"), ("aviso", "porcentaje_sin_marca")} <= resultado


def test_en_una_plantilla_sin_atleta_no_se_pide_marca_pero_un_kg_de_barra_sigue_siendo_un_error():
    r = buena()
    assert evaluar(r, prs=None) == []
    _sesiones(r)[0]["exercises"][0].update({"prescribed_percentage": None, "prescribed_weight": 100})
    assert [(h.nivel, h.regla) for h in evaluar(r, prs=None)] == [("error", "kg_inventado")]


def test_una_rampa_se_evalua_serie_por_serie():
    r = buena()
    # en la última sesión, para que la media de las semanas anteriores no cambie
    _sesiones(r)[-1]["exercises"][0]["series"] = [{"prescribed_reps": 3, "prescribed_percentage": 70}, {"prescribed_reps": 1, "prescribed_percentage": 140}]
    assert reglas(evaluar(r)) == ["porcentaje_absurdo"]


# ------------------------------------------------------------------ tamaño

def test_series_repeticiones_y_ejercicios_absurdos():
    r = buena()
    ej = _sesiones(r)[0]["exercises"][0]
    ej.update({"prescribed_sets": 500, "prescribed_reps": 900, "rpe_target": 14})
    assert {(h.nivel, h.regla) for h in evaluar(r)} == {("error", "series_absurdas"), ("error", "repeticiones_absurdas"), ("aviso", "rpe_fuera_de_rango")}

    r = buena()
    _sesiones(r)[0]["exercises"] = [copy.deepcopy(_sesion("x")["exercises"][0]) for _ in range(40)]
    assert "demasiados_ejercicios" in reglas(evaluar(r))
    r = buena()
    _sesiones(r)[0]["exercises"] = [copy.deepcopy(_sesion("x")["exercises"][0]) for _ in range(20)]
    assert reglas(evaluar(r)) == ["sesion_muy_larga"]


# ------------------------------------------------------------------ progresión

def test_la_intensidad_que_baja_o_que_no_cambia_es_un_aviso():
    r = buena()
    for i, semana in enumerate(r["weeks"]):
        for s in semana["sessions"]:
            s["exercises"][0]["prescribed_percentage"] = 85 - 5 * i
    assert reglas(evaluar(r)) == ["progresion_decreciente"]

    r = buena()
    for semana in r["weeks"]:
        for s in semana["sessions"]:
            s["exercises"][0]["prescribed_percentage"] = 75
    assert reglas(evaluar(r)) == ["sin_progresion"]


def test_una_descarga_a_mitad_del_bloque_no_es_un_problema():
    r = buena()
    for semana, porcentaje in zip(r["weeks"], (70, 80, 60, 85)):
        for s in semana["sessions"]:
            s["exercises"][0]["prescribed_percentage"] = porcentaje
    assert evaluar(r) == []


def test_con_menos_de_tres_semanas_no_se_evalua_la_progresion():
    r = {"weeks": [{"sessions": [_sesion(FECHAS[0], 80), _sesion(FECHAS[1], 80), _sesion(FECHAS[2], 70), _sesion(FECHAS[3], 70)]}]}
    assert evaluar(r, fechas=FECHAS[:4]) == []


# ------------------------------------------------------------------ enfoque por día

def test_el_enfoque_pedido_para_un_dia_debe_notarse_en_esa_sesion():
    r = buena()
    for s in _sesiones(r):
        s["wod"] = None   # el WOD de ejemplo menciona pull-ups: se quita para que "dominadas" no aparezca solo
    foco = {0: "Sentadilla pesada", 2: "Gimnasia y dominadas"}   # lunes y miércoles
    # los lunes hay Back Squat (equivale a "sentadilla"); los miércoles también, y no hay dominadas...
    assert reglas(evaluar(r, day_focus=foco)) == ["enfoque_no_reflejado"]
    # ...pero con dominadas en la sesión el aviso desaparece
    for s in _sesiones(r):
        if s["scheduled_date"] in FECHAS[1::2]:
            s["exercises"].append({"exercise_name": "Strict Pull-ups", "block": "skills", "prescribed_sets": 3, "prescribed_reps": 8})
    assert evaluar(r, day_focus=foco) == []


def test_sin_enfoque_o_con_uno_vacio_no_hay_nada_que_evaluar():
    assert evaluar(buena(), day_focus=None) == [] and evaluar(buena(), day_focus={0: "   "}) == []


# ------------------------------------------------------------------ robustez

@pytest.mark.parametrize("basura", [None, [], "texto", {}, {"error": "caído"}, {"weeks": "x"}, {"weeks": [{"sessions": [None, 5, "x"]}]}])
def test_una_respuesta_rota_no_rompe_la_evaluacion_y_se_ve_como_falta_de_sesiones(basura):
    hallazgos = evaluar(basura)
    assert all(isinstance(h, Hallazgo) for h in hallazgos)
    assert {h.regla for h in hallazgos} == {"sin_sesion"} and len(hallazgos) == len(FECHAS)


def test_ejercicios_con_formato_roto_no_rompen_la_evaluacion():
    r = buena()
    _sesiones(r)[0]["exercises"] = ["basura", None, {"exercise_name": 5, "block": 7, "prescribed_sets": "x", "series": "mal"}]
    evaluar(r)   # no lanza


# ------------------------------------------------------------------ uso de componentes

def test_uso_de_componentes_cuenta_lo_que_la_ia_aprovecho():
    r = buena()
    _sesiones(r)[0]["block_order"] = ["warmup", "metcon"]
    _sesiones(r)[0]["exercises"][0]["series"] = [{"prescribed_reps": 3, "prescribed_percentage": 70}, {"prescribed_reps": 1, "prescribed_percentage": 80}]
    _sesiones(r)[1]["warmup_notes"] = ""
    _sesiones(r)[1]["wod"] = None
    _sesiones(r)[1]["exercises"][0]["coach_note"] = None
    assert uso_de_componentes(r) == {
        "sesiones": 8, "con_calentamiento_en_texto": 7, "con_orden_de_bloques": 1, "con_wod": 7,
        "ejercicios": 8, "ejercicios_con_nota": 7, "ejercicios_con_rampa": 1,
    }
    assert uso_de_componentes(None)["sesiones"] == 0


def test_las_reglas_se_pueden_aplicar_a_un_json_guardado():
    """Lo que hace `python -m backend.evals.run_ia --archivo`: la respuesta viaja como JSON."""
    r = json.loads(json.dumps(buena()))
    assert evaluar(r) == []


# ------------------------------------------------------------------ el ejecutor manual (backend/evals/run_ia.py)

def test_el_ejecutor_evalua_un_json_guardado_sin_llamar_a_la_ia(tmp_path, capsys):
    from backend.evals import run_ia

    r = buena()
    _sesiones(r)[0]["exercises"][0].update({"exercise_name": "Front Squat", "reference_exercise": None,
                                            "prescribed_percentage": None, "prescribed_weight": 85})
    archivo = tmp_path / "respuesta.json"
    archivo.write_text(json.dumps(r), encoding="utf-8")
    codigo = run_ia.main(["--archivo", str(archivo), "--fechas", ",".join(FECHAS), "--marcas", "Back Squat=100"])
    salida = capsys.readouterr().out
    assert codigo == 1 and "kg_inventado" in salida and "'errores': 1" in salida     # un error de seguridad: el código de salida lo dice

    archivo.write_text(json.dumps(buena()), encoding="utf-8")
    assert run_ia.main(["--archivo", str(archivo), "--fechas", ",".join(FECHAS), "--marcas", "Back Squat=100"]) == 0


def test_el_ejecutor_corre_un_caso_completo_con_la_ia_simulada(monkeypatch, capsys):
    from backend import ai_agent
    from backend.evals import run_ia

    def falsa(**kw):
        sesiones = [_sesion(f) for f in kw["session_dates"]]
        return {"weeks": [{"sessions": sesiones}], "_uso": {"tokens_prompt": 100, "tokens_salida": 200, "tokens_pensamiento": 0}}

    monkeypatch.setattr(ai_agent, "generate_mesocycle_chunk", falsa)
    codigo = run_ia.main(["--caso", "mesociclo_largo_tres_tandas"])
    salida = capsys.readouterr().out
    assert "== mesociclo_largo_tres_tandas" in salida and "'llamadas': 3" in salida   # 8 semanas = 3 tandas
    assert "componentes usados" in salida and codigo in (0, 1)
    assert run_ia.main(["--caso", "no_existe"]) == 2


def test_el_ejecutor_reporta_una_tanda_que_fallo_como_error(monkeypatch, capsys):
    from backend import ai_agent
    from backend.evals import run_ia

    monkeypatch.setattr(ai_agent, "generate_mesocycle_chunk", lambda **kw: {"error": "Gemini caído"})
    assert run_ia.main(["--caso", "crossfit_sin_marcas"]) == 1
    assert "la_ia_fallo" in capsys.readouterr().out
