"""La generación con IA usa todos los componentes de una sesión armada a mano, no inventa cargas y
repara (o rechaza) lo que la IA hace mal. La llamada a Gemini se simula; ver también test_ia_pasos.py
(los pasos puros), test_ia_salida.py (la limpieza) y test_ia_mesociclos.py (el flujo básico)."""
from datetime import date, timedelta

import pytest

# El fixture `gemini` y los ayudantes del flujo básico se reutilizan tal cual
from backend.tests.test_ia_mesociclos import (  # noqa: F401
    HOY,
    _pedir,
    _pedir_plantilla,
    _series_del_atleta,
    gemini,
)


def _marca(atleta, ejercicio, kg):
    atleta.post(f"/users/{atleta.id}/records/", json={"exercise_name": ejercicio, "max_weight_kg": kg})


# ================================================================== todos los componentes de la sesión

def test_la_ia_usa_el_calentamiento_en_texto_el_orden_de_bloques_las_notas_y_las_rampas(coach, atleta_de_coach, gemini):
    _marca(atleta_de_coach, "Snatch", 80)
    gemini.extra_sesion = {"warmup_notes": "5 min de remo\n\n\n3 aproximaciones al primer set", "block_order": ["strength", "warmup", "inventado"]}
    gemini.ejercicios = [
        {"exercise_name": "Snatch", "block": "weightlifting", "prescribed_sets": 4, "prescribed_reps": 3, "rpe_target": 7,
         "coach_note": "Tirón completo\nrecepción firme", "reference_exercise": "Snatch", "series": [
             {"prescribed_reps": 3, "prescribed_percentage": 50}, {"prescribed_reps": 3, "prescribed_percentage": 60},
             {"prescribed_reps": 1, "prescribed_percentage": 70}, {"prescribed_reps": 1, "prescribed_percentage": 80}]},
        {"exercise_name": "Back Squat", "block": "strength", "prescribed_sets": 3, "prescribed_reps": 5, "rpe_target": 8},
    ]
    assert _pedir(coach, atleta_de_coach, weeks_count=1).status_code == 200
    _, sesiones, series = _series_del_atleta(coach, atleta_de_coach)
    sesion = sesiones[0]
    assert sesion["warmup_notes"] == "5 min de remo\n\n3 aproximaciones al primer set"      # texto en párrafo, con sus líneas
    assert sesion["block_order"] == "strength,warmup"                                       # sin el bloque inventado

    arranque = [s for s in series if s["exercise"]["name"] == "Snatch"]
    assert [(s["prescribed_reps"], s["prescribed_percentage"], s["prescribed_weight"]) for s in arranque] == [
        (3, 50, 40), (3, 60, 47.5), (1, 70, 55), (1, 80, 65)]                                  # rampa: cada serie con su carga
    assert {s["coach_note"] for s in arranque} == {"Tirón completo\nrecepción firme"}
    assert {s["coach_note"] for s in series if s["exercise"]["name"] == "Back Squat"} == {None}
    assert [s["set_order"] for s in sorted(series, key=lambda x: x["set_order"])] == list(range(1, len(series) + 1))


@pytest.mark.parametrize("formato", ["for_time", "amrap", "amrap_reps", "emom", "tabata", "1rm", "calories", "distance", "watts"])
def test_la_ia_puede_devolver_cualquiera_de_los_nueve_formatos_de_wod(coach, atleta_de_coach, gemini, formato):
    gemini.wod = {"name": "WOD", "format": formato, "time_cap_minutes": 12, "description": "3 rondas\nde lo que sea"}
    assert _pedir(coach, atleta_de_coach, weeks_count=1).status_code == 200
    sesion = _series_del_atleta(coach, atleta_de_coach)[1][0]
    assert sesion["wod_format"] == formato and sesion["wod_notes"] == "WOD\n3 rondas\nde lo que sea"


# ================================================================== cargas: nunca un kg inventado

def test_un_kg_inventado_para_un_levantamiento_sin_marca_se_descarta_y_se_avisa_al_coach(coach, atleta_de_coach, gemini):
    gemini.ejercicios = [
        {"exercise_name": "Back Squat", "block": "strength", "prescribed_sets": 3, "prescribed_reps": 5, "prescribed_weight": 100},
        {"exercise_name": "Dumbbell Row", "block": "accessory", "prescribed_sets": 3, "prescribed_reps": 10, "prescribed_weight": 22.5},
    ]
    r = _pedir(coach, atleta_de_coach, weeks_count=1)
    assert r.status_code == 200, r.text
    _, _, series = _series_del_atleta(coach, atleta_de_coach)
    assert {s["prescribed_weight"] for s in series if s["exercise"]["name"] == "Back Squat"} == {None}   # sin marca: carga libre
    assert {s["prescribed_weight"] for s in series if s["exercise"]["name"] == "Dumbbell Row"} == {22.5}  # un accesorio sí
    avisos = r.json()["advertencias"]
    assert len(avisos) == 1 and "Back Squat" in avisos[0] and str(HOY) in avisos[0]


def test_la_respuesta_trae_los_avisos_y_los_tokens_gastados_sumados_por_tanda(coach, atleta_de_coach, gemini, monkeypatch):
    from backend import ai_agent

    _marca(atleta_de_coach, "Back Squat", 100)   # con marca, el % del ejercicio de ejemplo se resuelve sin avisos
    original = ai_agent.generate_mesocycle_chunk

    def con_uso(**kw):
        return {**original(**kw), "_uso": {"tokens_prompt": 1000, "tokens_salida": 2000, "tokens_pensamiento": 50}}

    monkeypatch.setattr(ai_agent, "generate_mesocycle_chunk", con_uso)
    r = _pedir(coach, atleta_de_coach, weeks_count=7)   # tres tandas
    assert r.status_code == 200, r.text
    assert r.json()["advertencias"] == []
    assert r.json()["uso"] == {"llamadas": 3, "tokens_prompt": 3000, "tokens_salida": 6000, "tokens_pensamiento": 150}


def test_los_nombres_de_un_levantamiento_se_unifican_en_un_solo_ejercicio_del_catalogo(coach, atleta_de_coach, gemini):
    import uuid

    # El catálogo es compartido entre pruebas: un nombre propio de esta prueba para lo que no es un levantamiento
    propio = f"Remo-{uuid.uuid4().hex[:8]}"
    gemini.ejercicios = [
        {"exercise_name": "back squat", "prescribed_sets": 1, "prescribed_reps": 5, "block": "strength"},
        {"exercise_name": "Sentadilla trasera", "prescribed_sets": 1, "prescribed_reps": 5, "block": "strength"},
        {"exercise_name": "BACK SQUAT", "prescribed_sets": 1, "prescribed_reps": 5, "block": "strength"},
        {"exercise_name": propio.lower(), "prescribed_sets": 1, "prescribed_reps": 10, "block": "accessory"},
        {"exercise_name": propio.upper(), "prescribed_sets": 1, "prescribed_reps": 10, "block": "accessory"},
    ]
    assert _pedir(coach, atleta_de_coach, weeks_count=1).status_code == 200
    _, _, series = _series_del_atleta(coach, atleta_de_coach)
    assert {s["exercise"]["name"] for s in series} == {"Back Squat", propio.lower()}   # los levantamientos, canónicos; lo demás, el primero que llegó
    assert len({s["exercise"]["id"] for s in series}) == 2


# ================================================================== fechas y fallos de la IA

def _chunk_con(monkeypatch, comportamiento):
    """Sustituye la IA por `comportamiento(llamada_numero, kw) -> respuesta` y guarda las llamadas."""
    from backend import ai_agent

    llamadas = []

    def chunk(**kw):
        llamadas.append(kw)
        return comportamiento(len(llamadas), kw)

    monkeypatch.setattr(ai_agent, "generate_mesocycle_chunk", chunk)
    return llamadas


def _respuesta(fechas, **extra):
    return {"weeks": [{"sessions": [
        {"scheduled_date": f, "athlete_notes": "IA", "wod": None, **extra,
         "exercises": [{"exercise_name": "Push-up", "block": "accessory", "prescribed_sets": 2, "prescribed_reps": 10}]}
        for f in fechas]}]}


def _no_hay_mesociclo(coach, atleta):
    return all(m["name"] != "Bloque IA" for m in coach.get(f"/users/{atleta.id}/mesocycles/").json())


def test_una_tanda_que_falla_con_error_se_reintenta_una_vez_y_se_recupera(coach, atleta_de_coach, gemini, monkeypatch):
    llamadas = _chunk_con(monkeypatch, lambda n, kw: {"error": "Intenta de nuevo"} if n == 1 else _respuesta(kw["session_dates"]))
    assert _pedir(coach, atleta_de_coach, weeks_count=1).status_code == 200
    assert len(llamadas) == 2
    assert len(_series_del_atleta(coach, atleta_de_coach)[2]) == 2


def test_si_una_tanda_sigue_fallando_no_se_guarda_un_mesociclo_a_medias(coach, atleta_de_coach, gemini, monkeypatch):
    """El bug de antes: la IA real devuelve un diccionario con "error" (no lanza una excepción) y esa
    tanda pasaba como vacía: se guardaba un mesociclo al que le faltaban semanas, sin avisar."""
    llamadas = _chunk_con(monkeypatch, lambda n, kw: {"error": "Gemini saturado"} if kw["start_week"] == 4 else _respuesta(kw["session_dates"]))
    r = _pedir(coach, atleta_de_coach, weeks_count=7)
    assert r.status_code == 500 and "Semanas 4-6" in r.text and "Gemini saturado" in r.text
    assert _no_hay_mesociclo(coach, atleta_de_coach)
    assert sum(1 for c in llamadas if c["start_week"] == 4) == 2      # se reintentó solo la tanda que falló


def test_una_respuesta_que_no_es_un_objeto_tambien_cuenta_como_fallo(coach, atleta_de_coach, gemini, monkeypatch):
    _chunk_con(monkeypatch, lambda n, kw: None)
    r = _pedir(coach, atleta_de_coach, weeks_count=1)
    assert r.status_code == 500 and "respuesta inválida" in r.text and _no_hay_mesociclo(coach, atleta_de_coach)


def test_si_la_ia_se_salta_una_fecha_se_reintenta_la_tanda(coach, atleta_de_coach, gemini, monkeypatch):
    llamadas = _chunk_con(monkeypatch, lambda n, kw: _respuesta(kw["session_dates"][:-1] if n == 1 else kw["session_dates"]))
    assert _pedir(coach, atleta_de_coach, weeks_count=2).status_code == 200
    assert len(llamadas) == 2
    assert len(_series_del_atleta(coach, atleta_de_coach)[1]) == 2


def test_si_la_ia_sigue_sin_devolver_todas_las_fechas_se_rechaza_con_la_fecha_que_falta(coach, atleta_de_coach, gemini, monkeypatch):
    _chunk_con(monkeypatch, lambda n, kw: _respuesta(kw["session_dates"][:-1]))
    r = _pedir(coach, atleta_de_coach, weeks_count=2)
    assert r.status_code == 500 and str(HOY + timedelta(days=7)) in r.text and _no_hay_mesociclo(coach, atleta_de_coach)


def test_las_fechas_las_decide_el_calendario_del_coach_no_la_ia(coach, atleta_de_coach, gemini, monkeypatch):
    pedidas = []

    def inventa(n, kw):
        pedidas.extend(kw["session_dates"])
        return _respuesta(["1999-01-01", "no es una fecha"][: len(kw["session_dates"])])

    _chunk_con(monkeypatch, inventa)
    assert _pedir(coach, atleta_de_coach, weeks_count=2).status_code == 200
    fechas = sorted(s["scheduled_date"] for s in _series_del_atleta(coach, atleta_de_coach)[1])
    assert fechas == sorted(set(pedidas)) == [str(HOY), str(HOY + timedelta(days=7))]


def test_una_sesion_de_mas_o_repetida_se_descarta(coach, atleta_de_coach, gemini, monkeypatch):
    _chunk_con(monkeypatch, lambda n, kw: _respuesta(kw["session_dates"] + kw["session_dates"] + ["2030-01-01"]))
    assert _pedir(coach, atleta_de_coach, weeks_count=1).status_code == 200
    assert len(_series_del_atleta(coach, atleta_de_coach)[1]) == 1


def test_una_sesion_o_un_ejercicio_roto_no_tumba_el_mesociclo(coach, atleta_de_coach, gemini, monkeypatch):
    def rota(n, kw):
        buena = _respuesta(kw["session_dates"])
        sesion = buena["weeks"][0]["sessions"][0]
        sesion["exercises"] += ["basura", None, {"exercise_name": ["x"], "series": "mal"}, {"exercise_name": "Burpee", "prescribed_sets": 500}]
        return buena

    _chunk_con(monkeypatch, rota)
    r = _pedir(coach, atleta_de_coach, weeks_count=1)
    assert r.status_code == 200, r.text
    series = _series_del_atleta(coach, atleta_de_coach)[2]
    assert len([s for s in series if s["exercise"]["name"] == "Burpee"]) == 12    # 500 series se recortan a 12
    assert any("no tenía el formato esperado" in a for a in r.json()["advertencias"])


# ================================================================== plantillas

def test_la_plantilla_de_ia_descarta_un_kg_de_barra_pero_conserva_el_porcentaje_y_el_calentamiento(coach, gemini):
    gemini.extra_sesion = {"warmup_notes": "Movilidad 5 min\nAproximaciones"}
    gemini.ejercicios = [
        {"exercise_name": "Back Squat", "block": "strength", "prescribed_sets": 3, "prescribed_reps": 5, "prescribed_weight": 100},
        {"exercise_name": "Snatch", "block": "weightlifting", "prescribed_sets": 3, "prescribed_reps": 2, "prescribed_percentage": 70},
    ]
    plan = _pedir_plantilla(coach, weeks_count=1, training_days=[0]).json()
    sesion = coach.get(f"/plans/{plan['id']}").json()["sessions"][0]
    assert sesion["warmup_notes"] == "Movilidad 5 min\nAproximaciones"
    por_nombre = {n: [s for s in sesion["sets"] if s["exercise"]["name"] == n] for n in ("Back Squat", "Snatch")}
    assert {(s["prescribed_weight"], s["prescribed_percentage"]) for s in por_nombre["Back Squat"]} == {(None, None)}
    assert {(s["prescribed_weight"], s["prescribed_percentage"]) for s in por_nombre["Snatch"]} == {(None, 70)}


def test_la_plantilla_de_ia_tambien_se_rechaza_si_falta_una_fecha(coach, gemini, monkeypatch):
    _chunk_con(monkeypatch, lambda n, kw: _respuesta(kw["session_dates"][:-1]))
    r = _pedir_plantilla(coach)
    assert r.status_code == 500 and coach.get("/plans/mine").json() == []


# ================================================================== una sesión suelta

def test_la_sesion_suelta_ahora_respeta_las_series_el_calentamiento_y_la_nota(coach, atleta_de_coach, monkeypatch):
    from backend import ai_agent

    _marca(atleta_de_coach, "Back Squat", 100)
    monkeypatch.setattr(ai_agent, "generate_workout_session", lambda **kw: {
        "session_focus": "Fuerza", "athlete_notes": "Vamos", "warmup_notes": "5 min de bici\nAproximaciones",
        "exercises": [
            {"exercise_name": "Back Squat", "block": "strength", "prescribed_sets": 3, "prescribed_reps": 5, "rpe_target": 8,
             "prescribed_percentage": 80, "reference_exercise": "Back Squat", "coach_note": "Profundidad"},
            {"prescribed_reps": 5},                       # sin nombre: antes rompía la petición
        ],
    })
    creado = coach.post("/mesocycles/manual", json={
        "user_id": atleta_de_coach.id, "name": "Base", "discipline": "CrossFit",
        "start_date": str(HOY), "weeks_count": 1, "training_days": [HOY.weekday()],
    }).json()
    r = coach.post("/ai/generate-session/", json={"mesocycle_id": creado["mesocycle_id"], "context": "x", "weeks_count": 1, "sessions_per_week": 1})
    assert r.status_code == 200, r.text
    sesiones = coach.get(f"/mesocycles/{creado['mesocycle_id']}").json()["sessions"]
    generada = next(s for s in sesiones if s["warmup_notes"])
    assert generada["warmup_notes"] == "5 min de bici\nAproximaciones"
    squat = [s for s in generada["sets"] if s["exercise"]["name"] == "Back Squat"]
    assert len(squat) == 3                                                   # antes se guardaba UNA serie por ejercicio
    assert {(s["prescribed_weight"], s["coach_note"]) for s in squat} == {(80, "Profundidad")}
    assert len(generada["sets"]) == 4                                        # + el ejercicio sin nombre, con valores por defecto


def test_el_mismo_problema_en_varias_sesiones_es_un_solo_aviso(coach, atleta_de_coach, gemini):
    gemini.ejercicios = [{"exercise_name": "Back Squat", "block": "strength", "prescribed_sets": 3, "prescribed_reps": 5, "prescribed_weight": 100}]
    r = _pedir(coach, atleta_de_coach, weeks_count=2)   # dos sesiones con el mismo kg inventado
    assert r.status_code == 200, r.text
    avisos = r.json()["advertencias"]
    assert len(avisos) == 1 and "Back Squat" in avisos[0] and avisos[0].endswith("(en 2 sesiones)")
