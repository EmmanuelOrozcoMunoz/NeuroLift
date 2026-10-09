"""El texto largo que alguien escribe en varias líneas (un WOD, el calentamiento, una nota) conserva
sus saltos de línea al guardarse; los campos de una sola línea (nombres...) siguen colapsándose."""
from datetime import date

import pytest

from backend.sanitize import clean_multiline, clean_text

HOY = date.today()
WOD = "21-15-9\nThrusters 42kg\nPull-ups\n\nTime cap 12 min"


# ------------------------------------------------------------------ el sanitizador

def test_clean_multiline_conserva_los_saltos_de_linea_y_una_linea_en_blanco():
    assert clean_multiline(WOD) == WOD
    assert clean_multiline("AMRAP 12 min:\n- 5 pull-ups\n- 10 push-ups") == "AMRAP 12 min:\n- 5 pull-ups\n- 10 push-ups"


def test_clean_multiline_normaliza_los_distintos_saltos_de_linea():
    # Windows (\r\n), Mac antiguo (\r) y los separadores Unicode llegan como un salto normal
    assert clean_multiline("a\r\nb\rc d e") == "a\nb\nc\nd\ne"


def test_clean_multiline_colapsa_espacios_solo_dentro_de_cada_linea():
    assert clean_multiline("  Fran:\t21-15-9   thrusters  \n   pull-ups   ") == "Fran: 21-15-9 thrusters\npull-ups"


def test_clean_multiline_deja_como_mucho_una_linea_en_blanco_seguida():
    assert clean_multiline("a\n\n\n\n\nb\n \n \n \nc") == "a\n\nb\n\nc"
    assert clean_multiline("\n\n  hola  \n\n") == "hola"
    assert clean_multiline("   \n  \t ") == ""


@pytest.mark.parametrize("entrada, esperado", [
    ("Hacer <b>mucho</b> cuidado", "Hacer mucho cuidado"),
    ("línea 1\n<script>alert(1)</script>línea 2", "línea 1\nalert(1)línea 2"),
    ('<img src=x onerror="alert(1)">hola\nmundo', "hola\nmundo"),
])
def test_clean_multiline_sigue_quitando_el_html(entrada, esperado):
    assert clean_multiline(entrada) == esperado


def test_clean_multiline_no_toca_los_signos_que_no_son_etiquetas():
    assert clean_multiline("Clean & Jerk 5 < 10 reps\nRPE>7 y <5 reps>") == "Clean & Jerk 5 < 10 reps\nRPE>7 y <5 reps>"


def test_clean_multiline_quita_nulos_trunca_y_deja_pasar_lo_que_no_es_texto():
    assert clean_multiline("a\x00b\nc") == "ab\nc"
    assert clean_multiline("a\nb\nc", max_length=3) == "a\nb"
    assert clean_multiline(None) is None
    assert clean_multiline(5) == 5


def test_clean_text_sigue_colapsando_todo_a_una_linea():
    """Nombres, correos y títulos no deben poder traer saltos de línea."""
    assert clean_text("Ana\nPérez\t  López") == "Ana Pérez López"
    assert clean_text(WOD) == "21-15-9 Thrusters 42kg Pull-ups Time cap 12 min"


# ------------------------------------------------------------------ qué campos conservan los saltos

def test_los_campos_de_texto_largo_conservan_los_saltos_y_los_demas_no():
    from backend.schemas import PlanCreate, SessionMetaUpdate, SetCreate

    meta = SessionMetaUpdate(wod_notes=WOD, warmup_notes="5 min de movilidad\n3 aproximaciones")
    assert meta.wod_notes == WOD and meta.warmup_notes == "5 min de movilidad\n3 aproximaciones"

    serie = SetCreate(exercise_name="Back\nSquat", prescribed_reps=5, coach_note="Codos arriba\nPausa abajo")
    assert serie.coach_note == "Codos arriba\nPausa abajo"
    assert serie.exercise_name == "Back Squat"  # el nombre del ejercicio es de una línea

    plan = PlanCreate(name="Fuerza\nbase", description="Semana 1: base\nSemana 2: volumen", discipline="CrossFit",
                      weeks_count=2, training_days=[0])
    assert plan.description == "Semana 1: base\nSemana 2: volumen"
    assert plan.name == "Fuerza base"


def test_la_contrasena_no_se_toca():
    from backend.schemas import UserRegister

    r = UserRegister(email="a@b.co", full_name="Ana", password="  con  espacios\ny salto  ")
    assert r.password == "  con  espacios\ny salto  "


# ------------------------------------------------------------------ de punta a punta por la API

@pytest.fixture
def sesion(coach, atleta_de_coach):
    meso = coach.post("/mesocycles/manual", json={
        "user_id": atleta_de_coach.id, "name": "Base", "discipline": "CrossFit",
        "start_date": str(HOY), "weeks_count": 1, "training_days": [HOY.weekday()],
    }).json()
    sesion_id = coach.get(f"/mesocycles/{meso['mesocycle_id']}").json()["sessions"][0]["id"]
    return meso["mesocycle_id"], sesion_id


def test_el_wod_y_el_calentamiento_de_una_sesion_vuelven_igual_que_se_escribieron(coach, atleta_de_coach, sesion):
    meso_id, sesion_id = sesion
    r = coach.put(f"/sessions/{sesion_id}/meta", json={"wod_notes": WOD, "warmup_notes": "5 min\n\n3 aproximaciones"})
    assert r.status_code == 200, r.text
    assert r.json()["wod_notes"] == WOD

    # lo que lee el atleta es lo mismo, con sus saltos de línea
    leida = atleta_de_coach.get(f"/mesocycles/{meso_id}").json()["sessions"][0]
    assert leida["wod_notes"] == WOD
    assert leida["warmup_notes"] == "5 min\n\n3 aproximaciones"


def test_el_html_en_un_wod_se_quita_sin_perder_las_lineas(coach, sesion):
    _, sesion_id = sesion
    r = coach.put(f"/sessions/{sesion_id}/meta", json={"wod_notes": "Fran\n<script>alert(1)</script>21-15-9"})
    assert r.status_code == 200
    assert r.json()["wod_notes"] == "Fran\nalert(1)21-15-9"


def test_el_wod_de_un_plan_conserva_las_lineas_y_llega_igual_al_atleta(coach, atleta_de_coach):
    plan = coach.post("/plans/", json={
        "name": "Plan WOD", "description": "Semana 1\nSemana 2", "discipline": "CrossFit", "level": "Intermedio",
        "weeks_count": 1, "training_days": [0],
    }).json()
    dia = coach.get(f"/plans/{plan['id']}").json()["sessions"][0]["id"]
    r = coach.post(f"/plans/{plan['id']}/sessions/{dia}/sets", json={
        "exercise_name": "Back Squat", "prescribed_sets": 1, "prescribed_reps": 5, "prescribed_weight": 60, "block": "strength",
    })
    assert r.status_code == 200, r.text
    r = coach.put(f"/plans/{plan['id']}/sessions/{dia}/meta", json={"wod_notes": WOD, "warmup_notes": "a\nb"})
    assert r.status_code == 200 and r.json()["wod_notes"] == WOD

    assert coach.put(f"/plans/{plan['id']}/publish", json={"is_published": True}).status_code == 200
    adquirido = atleta_de_coach.post(f"/plans/{plan['id']}/acquire", json={"start_date": str(HOY)})
    assert adquirido.status_code == 200, adquirido.text
    meso = atleta_de_coach.get(f"/mesocycles/{adquirido.json()['mesocycle_id']}").json()
    assert meso["sessions"][0]["wod_notes"] == WOD and meso["sessions"][0]["warmup_notes"] == "a\nb"
    assert coach.get(f"/plans/{plan['id']}").json()["description"] == "Semana 1\nSemana 2"


def test_la_nota_del_coach_por_ejercicio_conserva_las_lineas(coach, sesion):
    _, sesion_id = sesion
    r = coach.post(f"/sessions/{sesion_id}/sets/", json={
        "exercise_name": "Back Squat", "prescribed_reps": 5, "prescribed_weight": 80,
        "coach_note": "Codos arriba\nPausa abajo",
    })
    assert r.status_code == 200, r.text
    series = coach.get(f"/mesocycles/{sesion[0]}").json()["sessions"][0]["sets"]
    assert series[0]["coach_note"] == "Codos arriba\nPausa abajo"


def test_el_nombre_de_un_atleta_sigue_siendo_de_una_linea(client, codigo_coach):
    from backend.tests.conftest import PASSWORD, _email, _login

    email = _email("saltos")
    r = client.post("/auth/register", json={"email": email, "full_name": "Ana\nMaría\t Pérez", "password": PASSWORD, "invite_code": codigo_coach})
    assert r.status_code == 200, r.text
    assert _login(client, email).datos["full_name"] == "Ana María Pérez"


# ------------------------------------------------------------------ el WOD que genera la IA

def test_el_wod_de_la_ia_conserva_las_lineas_de_la_descripcion_y_quita_html():
    from backend.services.ai_mesocycles import wod_limpio

    r = wod_limpio({"name": " Fran  ", "format": "for_time", "time_cap_minutes": 10,
                    "description": "21-15-9\nThrusters (43/30 kg)\n\n\nPull-ups <b>estrictos</b>"})
    assert r["notes"] == "Fran\n21-15-9\nThrusters (43/30 kg)\n\nPull-ups estrictos"
    assert wod_limpio({"format": "for_time", "name": "  ", "description": "   \n  "}) == {
        "format": "for_time", "time_cap_seconds": None, "notes": None}
