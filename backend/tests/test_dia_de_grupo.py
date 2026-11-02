"""Programar un día para todo un grupo desde el calendario: cada miembro recibe una sesión vacía ese día
en el programa "Programación diaria" del grupo, que se edita con los mismos editores de grupo."""
import uuid
from datetime import date, timedelta

from backend.tests.test_asignar_plan import _atleta, grupo, plantilla, _asignar  # noqa: F401  (fixtures y ayudas)

HOY = date.today()
LUNES = HOY + timedelta(days=(7 - HOY.weekday()) % 7 or 7)


def _dia(coach, g, fecha):
    return coach.post(f"/groups/{g['id']}/days", json={"date": str(fecha)})


def _programas(coach, g):
    return coach.get(f"/groups/{g['id']}/mesocycles").json()


def _sesiones_del_atleta(atleta):
    todas = []
    for meso in atleta.get(f"/users/{atleta.id}/mesocycles/").json():
        todas += atleta.get(f"/mesocycles/{meso['id']}").json()["sessions"]
    return todas


def test_programar_un_dia_crea_la_sesion_de_cada_miembro_en_el_programa_diario(coach, grupo):
    g, ana, beto = grupo
    r = _dia(coach, g, LUNES)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["program_name"] == "Programación diaria"
    assert cuerpo["program_start_date"] == str(LUNES) and cuerpo["scheduled_date"] == str(LUNES)
    assert cuerpo["created"] is True and cuerpo["athletes"] == 2

    for atleta in (ana, beto):
        sesiones = _sesiones_del_atleta(atleta)
        assert [(s["scheduled_date"], s["status"], s["sets"]) for s in sesiones] == [(str(LUNES), "pending", [])]

    programas = _programas(coach, g)
    assert len(programas) == 1
    assert programas[0]["name"] == "Programación diaria" and len(programas[0]["athletes"]) == 2
    assert programas[0]["session_dates"] == [str(LUNES)]


def test_pedir_el_mismo_dia_otra_vez_no_duplica_nada(coach, grupo):
    g, ana, _ = grupo
    primero = _dia(coach, g, LUNES).json()
    segundo = _dia(coach, g, LUNES)
    assert segundo.status_code == 200
    assert segundo.json()["created"] is False
    assert segundo.json()["program_start_date"] == primero["program_start_date"]
    assert len(_sesiones_del_atleta(ana)) == 1


def test_varios_dias_van_al_mismo_programa_y_uno_anterior_no_cambia_su_identidad(coach, grupo):
    g, ana, _ = grupo
    miercoles = LUNES + timedelta(days=2)
    antes = LUNES - timedelta(days=7)
    inicio = _dia(coach, g, LUNES).json()["program_start_date"]
    assert _dia(coach, g, miercoles).json()["program_start_date"] == inicio
    # un día ANTERIOR al primero no mueve la fecha de inicio (junto con el nombre identifica al programa)
    assert _dia(coach, g, antes).json()["program_start_date"] == inicio

    programas = _programas(coach, g)
    assert len(programas) == 1
    assert programas[0]["start_date"] == inicio
    assert programas[0]["session_dates"] == [str(antes), str(LUNES), str(miercoles)]
    assert programas[0]["end_date"] == str(miercoles)
    assert sorted(s["scheduled_date"] for s in _sesiones_del_atleta(ana)) == [str(antes), str(LUNES), str(miercoles)]


def test_el_dia_programado_se_edita_con_los_editores_de_grupo(coach, grupo):
    g, ana, beto = grupo
    r = _dia(coach, g, LUNES).json()
    base = {"program_name": r["program_name"], "program_start_date": r["program_start_date"], "scheduled_date": r["scheduled_date"]}
    assert coach.post(f"/groups/{g['id']}/sessions/bulk-set-block-notes", json={**base, "block": "strength", "block_text": "Sentadilla 5x5"}).status_code == 200
    assert coach.post(f"/groups/{g['id']}/sessions/bulk-set-wod-notes", json={**base, "wod_notes": "21-15-9 thrusters"}).status_code == 200
    for atleta in (ana, beto):
        sesion = _sesiones_del_atleta(atleta)[0]
        assert sesion["block_notes"] == {"strength": "Sentadilla 5x5"} and sesion["wod_notes"] == "21-15-9 thrusters"


def test_un_miembro_que_se_une_despues_recibe_los_dias_ya_programados(client, coach, codigo_coach, grupo):
    g, *_ = grupo
    _dia(coach, g, LUNES)
    carla = _atleta(client, codigo_coach, "Carla")
    assert coach.post(f"/groups/{g['id']}/members", json={"athlete_ids": [carla.id]}).status_code == 200
    assert [s["scheduled_date"] for s in _sesiones_del_atleta(carla)] == [str(LUNES)]
    # y el siguiente día que se programe también le llega a ella
    _dia(coach, g, LUNES + timedelta(days=1))
    assert len(_sesiones_del_atleta(carla)) == 2
    assert len(_programas(coach, g)) == 1


def test_un_miembro_sin_programa_diario_lo_recibe_al_programar_un_dia_nuevo(client, coach, codigo_coach, grupo):
    g, *_ = grupo
    carla = _atleta(client, codigo_coach, "Carla")
    # ella entra al grupo ANTES de que exista el programa diario
    assert coach.post(f"/groups/{g['id']}/members", json={"athlete_ids": [carla.id]}).status_code == 200
    _dia(coach, g, LUNES)
    assert [s["scheduled_date"] for s in _sesiones_del_atleta(carla)] == [str(LUNES)]


def test_el_programa_diario_convive_con_otros_programas_del_grupo(coach, grupo, plantilla):
    g, ana, _ = grupo
    assert _asignar(coach, g, plantilla).status_code == 200
    _dia(coach, g, LUNES)
    nombres = sorted(p["name"] for p in _programas(coach, g))
    assert nombres == ["Fuerza base", "Programación diaria"]


def test_grupo_vacio_fecha_absurda_y_permisos(client, coach, grupo, dueno_de_box):
    g, ana, _ = grupo
    vacio = coach.post("/groups/", json={"name": "Nadie", "athlete_ids": []}).json()
    assert _dia(coach, vacio, LUNES).status_code == 400
    assert _dia(coach, g, date(2001, 1, 1)).status_code == 400
    assert _dia(coach, g, HOY + timedelta(days=900)).status_code == 400
    assert _dia(dueno_de_box, g, LUNES).status_code in (403, 404)     # grupo de otro coach
    assert _dia(ana, g, LUNES).status_code == 403                      # un atleta no programa
    assert coach.post(f"/groups/{g['id']}/days", json={"date": "no-es-fecha"}).status_code == 422
    assert coach.post(f"/groups/{uuid.uuid4()}/days", json={"date": str(LUNES)}).status_code == 404
