"""Asignar una plantilla (plan) del coach a un grupo: cada atleta recibe su copia con las cargas en
% calculadas con SUS marcas, sin pasar por la IA."""
import uuid
from datetime import date, timedelta

import pytest

from backend.tests.conftest import PASSWORD, Cuenta, _login

HOY = date.today()
SALIDA = HOY + timedelta(days=3)


def _atleta(client, codigo, nombre) -> Cuenta:
    email = f"{nombre.lower()}-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "full_name": nombre, "password": PASSWORD, "invite_code": codigo})
    assert r.status_code == 200, r.text
    return _login(client, email)


def _marca(cuenta, ejercicio, kg):
    r = cuenta.post(f"/users/{cuenta.id}/records/", json={"exercise_name": ejercicio, "max_weight_kg": kg})
    assert r.status_code == 200, r.text


@pytest.fixture
def plantilla(coach):
    """Plan en borrador de 2 semanas, 2 días por semana, con Back Squat al 80% y un WOD."""
    plan = coach.post("/plans/", json={
        "name": "Fuerza base", "description": "", "discipline": "CrossFit", "level": "Intermedio",
        "weeks_count": 2, "training_days": [0, 3],
    }).json()
    detalle = coach.get(f"/plans/{plan['id']}").json()
    primera = detalle["sessions"][0]["id"]
    r = coach.post(f"/plans/{plan['id']}/sessions/{primera}/sets", json={
        "exercise_name": "Back Squat", "prescribed_sets": 3, "prescribed_reps": 5,
        "prescribed_percentage": 80, "reference_exercise": "Back Squat", "block": "strength",
    })
    assert r.status_code == 200, r.text
    r = coach.put(f"/plans/{plan['id']}/sessions/{primera}/wod-format", json={"wod_format": "for_time", "time_cap_seconds": 600})
    assert r.status_code == 200, r.text
    r = coach.put(f"/plans/{plan['id']}/sessions/{primera}/meta", json={"block_order": "metcon,strength"})
    assert r.status_code == 200, r.text
    return plan


@pytest.fixture
def grupo(client, coach, codigo_coach):
    ana = _atleta(client, codigo_coach, "Ana")
    beto = _atleta(client, codigo_coach, "Beto")
    g = coach.post("/groups/", json={"name": "Mañanas", "athlete_ids": [ana.id, beto.id]}).json()
    return g, ana, beto


def _asignar(coach, grupo, plan, fecha=SALIDA):
    return coach.post(f"/groups/{grupo['id']}/assign-plan", json={"plan_id": plan["id"], "start_date": str(fecha)})


def _mesociclo(cuenta, nombre="Fuerza base"):
    return next(m for m in cuenta.get(f"/users/{cuenta.id}/mesocycles/").json() if m["name"] == nombre)


def test_cada_atleta_recibe_el_plan_con_sus_kg_calculados_con_su_marca(coach, grupo, plantilla):
    g, ana, beto = grupo
    _marca(ana, "Back Squat", 100)
    _marca(beto, "Back Squat", 150)

    r = _asignar(coach, g, plantilla)
    assert r.status_code == 200, r.text
    assert [x["status"] for x in r.json()["results"]] == ["assigned", "assigned"]

    for atleta, kg in ((ana, 80), (beto, 120)):
        meso = atleta.get(f"/mesocycles/{_mesociclo(atleta)['id']}").json()
        series = [s for ses in meso["sessions"] for s in ses["sets"]]
        assert {(s["prescribed_weight"], s["prescribed_percentage"]) for s in series} == {(kg, 80)}
        assert len(series) == 3


def test_las_fechas_arrancan_en_la_fecha_elegida_y_se_conserva_el_patron_semanal(coach, grupo, plantilla):
    g, ana, _ = grupo
    _asignar(coach, g, plantilla)
    sesiones = ana.get(f"/mesocycles/{_mesociclo(ana)['id']}").json()["sessions"]
    fechas = sorted(s["scheduled_date"] for s in sesiones)
    assert len(fechas) == 4 and fechas[0] == str(SALIDA)
    assert fechas[2] == str(SALIDA + timedelta(days=7))      # la semana 2 repite el patrón


def test_el_programa_aparece_en_el_grupo_con_los_dos_atletas(coach, grupo, plantilla):
    g, ana, beto = grupo
    _asignar(coach, g, plantilla)
    programas = coach.get(f"/groups/{g['id']}/mesocycles").json()
    assert len(programas) == 1 and programas[0]["name"] == "Fuerza base"
    assert {a["full_name"] for a in programas[0]["athletes"]} == {"Ana", "Beto"}


def test_el_wod_y_el_orden_de_bloques_de_la_plantilla_llegan_al_atleta(coach, grupo, plantilla):
    g, ana, _ = grupo
    _asignar(coach, g, plantilla)
    sesiones = sorted(ana.get(f"/mesocycles/{_mesociclo(ana)['id']}").json()["sessions"], key=lambda s: s["scheduled_date"])
    assert sesiones[0]["wod_format"] == "for_time" and sesiones[0]["wod_time_cap_seconds"] == 600
    assert sesiones[0]["block_order"] == "metcon,strength"


def test_sin_marca_la_carga_queda_en_porcentaje_y_se_avisa(coach, grupo, plantilla):
    g, ana, beto = grupo
    _marca(ana, "Back Squat", 100)
    resultados = {x["full_name"]: x for x in _asignar(coach, g, plantilla).json()["results"]}
    assert resultados["Ana"]["missing_prs"] == []
    assert resultados["Beto"]["missing_prs"] == ["Back Squat"]
    series = [s for ses in beto.get(f"/mesocycles/{_mesociclo(beto)['id']}").json()["sessions"] for s in ses["sets"]]
    assert {(s["prescribed_weight"], s["prescribed_percentage"]) for s in series} == {(None, 80)}


def test_asignar_otra_vez_solo_llega_a_los_miembros_nuevos(client, coach, codigo_coach, grupo, plantilla):
    g, ana, beto = grupo
    _asignar(coach, g, plantilla)
    carla = _atleta(client, codigo_coach, "Carla")
    assert coach.post(f"/groups/{g['id']}/members", json={"athlete_ids": [carla.id]}).status_code == 200

    r = _asignar(coach, g, plantilla)
    assert r.status_code == 200, r.text
    estados = {x["full_name"]: x["status"] for x in r.json()["results"]}
    assert estados == {"Ana": "skipped", "Beto": "skipped", "Carla": "assigned"}
    assert len([m for m in ana.get(f"/users/{ana.id}/mesocycles/").json() if m["name"] == "Fuerza base"]) == 1


def test_la_misma_plantilla_sirve_en_otra_fecha_u_otro_grupo(client, coach, codigo_coach, grupo, plantilla):
    g, ana, _ = grupo
    _asignar(coach, g, plantilla)
    assert _asignar(coach, g, plantilla, SALIDA + timedelta(days=28)).status_code == 200
    assert len([m for m in ana.get(f"/users/{ana.id}/mesocycles/").json() if m["name"] == "Fuerza base"]) == 2

    dani = _atleta(client, codigo_coach, "Dani")
    otro = coach.post("/groups/", json={"name": "Tardes", "athlete_ids": [dani.id]}).json()
    assert _asignar(coach, otro, plantilla).status_code == 200
    assert _mesociclo(dani)["name"] == "Fuerza base"


def test_el_plan_original_no_se_toca_al_asignarlo(coach, grupo, plantilla):
    g, *_ = grupo
    antes = coach.get(f"/plans/{plantilla['id']}").json()
    _asignar(coach, g, plantilla)
    despues = coach.get(f"/plans/{plantilla['id']}").json()
    assert antes == despues
    assert [p["id"] for p in coach.get("/plans/mine").json()] == [plantilla["id"]]


def test_un_plan_sin_ejercicios_o_un_grupo_vacio_no_se_pueden_asignar(coach, grupo):
    g, *_ = grupo
    vacio = coach.post("/plans/", json={"name": "Vacío", "discipline": "CrossFit", "weeks_count": 1, "training_days": [0]}).json()
    assert _asignar(coach, g, vacio).status_code == 400

    sin_miembros = coach.post("/groups/", json={"name": "Nadie", "athlete_ids": []}).json()
    assert _asignar(coach, sin_miembros, vacio).status_code == 400


def test_no_se_puede_asignar_un_plan_ajeno_ni_a_un_grupo_ajeno(client, coach, grupo, plantilla, dueno_de_box):
    g, *_ = grupo
    otro_coach = dueno_de_box
    # el plan es de `coach`: otro coach no puede usarlo
    ajeno = otro_coach.post("/groups/", json={"name": "Suyo", "athlete_ids": []}).json()
    assert _asignar(otro_coach, ajeno, plantilla).status_code in (403, 404)
    # y un grupo ajeno no se puede tocar con un plan propio
    propio = otro_coach.post("/plans/", json={"name": "Mío", "discipline": "CrossFit", "weeks_count": 1, "training_days": [0]}).json()
    assert _asignar(otro_coach, g, propio).status_code in (403, 404)


def test_un_atleta_no_puede_asignar_planes(grupo, plantilla):
    g, ana, _ = grupo
    assert ana.post(f"/groups/{g['id']}/assign-plan", json={"plan_id": plantilla["id"], "start_date": str(SALIDA)}).status_code == 403
