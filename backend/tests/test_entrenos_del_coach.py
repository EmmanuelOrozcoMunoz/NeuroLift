"""Entrenos del coach, todos juntos: lo programado para sus grupos y para cada atleta personalizado, en un rango
de fechas. Un día de un grupo es UN entreno; uno personalizado es el de ese atleta."""
from datetime import date, timedelta

from backend.tests.test_asignar_plan import _atleta, grupo, plantilla, _asignar  # noqa: F401  (fixtures y ayudas)

HOY = date.today()
LUNES = HOY + timedelta(days=(7 - HOY.weekday()) % 7 or 7)


def _entrenos(cuenta, desde=None, hasta=None):
    return cuenta.get("/coach/trainings", params={
        "date_from": str(desde or LUNES - timedelta(days=30)), "date_to": str(hasta or LUNES + timedelta(days=60)),
    })


def _dia_de_grupo(coach, g, fecha):
    return coach.post(f"/groups/{g['id']}/days", json={"date": str(fecha)}).json()


def _dia_de_atleta(coach, atleta, fecha):
    return coach.post(f"/users/{atleta.id}/days", json={"date": str(fecha)}).json()


def test_sin_nada_programado_la_lista_esta_vacia(coach):
    r = _entrenos(coach)
    assert r.status_code == 200 and r.json() == []


def test_un_dia_de_grupo_es_un_solo_entreno_y_uno_personalizado_es_del_atleta(coach, grupo, atleta_de_coach):
    g, ana, beto = grupo
    _dia_de_grupo(coach, g, LUNES)
    _dia_de_atleta(coach, atleta_de_coach, LUNES + timedelta(days=1))

    items = _entrenos(coach).json()
    assert [(i["date"], i["kind"]) for i in items] == [(str(LUNES), "group"), (str(LUNES + timedelta(days=1)), "athlete")]

    grupal, personal = items
    assert grupal["group_id"] == g["id"] and grupal["group_name"] == "Mañanas" and grupal["athlete_id"] is None
    assert grupal["athletes_total"] == 2 and grupal["athletes_completed"] == 0
    assert grupal["program_name"] == "Programación diaria" and grupal["program_start_date"] == str(LUNES)
    assert personal["athlete_id"] == atleta_de_coach.id and personal["athlete_name"] == "Atleta Prueba"
    assert personal["group_id"] is None and personal["athletes_total"] == 1
    assert grupal["is_empty"] is True and grupal["blocks"] == [] and grupal["exercise_count"] == 0


def test_el_resumen_muestra_los_bloques_escritos_y_los_ejercicios(coach, atleta_de_coach):
    dia = _dia_de_atleta(coach, atleta_de_coach, LUNES)
    coach.put(f"/sessions/{dia['session_id']}/meta", json={
        "warmup_notes": "Movilidad", "block_notes": {"accessory": "Remo 3x10", "strength": "Sentadilla"},
        "block_order": "strength,warmup,accessory",
    })
    coach.put(f"/sessions/{dia['session_id']}/wod-format", json={"wod_format": "for_time", "time_cap_seconds": 600})
    coach.post(f"/sessions/{dia['session_id']}/sets/", json={
        "exercise_name": "Back Squat", "prescribed_sets": 3, "prescribed_reps": 5, "block": "weightlifting",
    })
    item = _entrenos(coach).json()[0]
    # primero el orden que eligió el coach (strength, warmup, accessory) y después los demás en su orden de siempre
    assert item["blocks"] == ["strength", "warmup", "accessory", "weightlifting", "metcon"]
    assert item["exercise_count"] == 1 and item["is_empty"] is False


def test_cuantos_del_grupo_ya_lo_terminaron(coach, grupo):
    g, ana, beto = grupo
    dia = _dia_de_grupo(coach, g, LUNES)
    sesion_de_ana = next(s for s in _sesiones(ana) if s["scheduled_date"] == str(LUNES))
    coach.put(f"/sessions/{sesion_de_ana['id']}/meta", json={"block_notes": {"strength": "x"}})   # que no esté vacío
    assert ana.post(f"/sessions/{sesion_de_ana['id']}/complete").status_code == 200
    item = _entrenos(coach).json()[0]
    assert (item["athletes_total"], item["athletes_completed"]) == (2, 1)
    assert dia["created"] is True


def _sesiones(atleta):
    todas = []
    for meso in atleta.get(f"/users/{atleta.id}/mesocycles/").json():
        todas += atleta.get(f"/mesocycles/{meso['id']}").json()["sessions"]
    return todas


def test_el_rango_de_fechas_filtra_y_los_extremos_se_incluyen(coach, atleta_de_coach):
    for dias in (0, 7, 14):
        _dia_de_atleta(coach, atleta_de_coach, LUNES + timedelta(days=dias))
    fechas = [i["date"] for i in _entrenos(coach, LUNES + timedelta(days=7), LUNES + timedelta(days=14)).json()]
    assert fechas == [str(LUNES + timedelta(days=7)), str(LUNES + timedelta(days=14))]
    assert _entrenos(coach, LUNES + timedelta(days=1), LUNES + timedelta(days=6)).json() == []


def test_un_plan_el_registro_propio_y_los_planes_asignados_se_tratan_como_corresponde(coach, grupo, plantilla, atleta_solo):
    g, ana, _ = grupo
    # una plantilla sin asignar NO es un entreno
    assert _entrenos(coach, HOY - timedelta(days=100), HOY + timedelta(days=300)).json() == []
    assert _asignar(coach, g, plantilla).status_code == 200      # asignada a un grupo: sí, como entreno del grupo
    items = _entrenos(coach, HOY, HOY + timedelta(days=60)).json()
    assert items and all(i["kind"] == "group" and i["group_id"] == g["id"] for i in items)
    assert all(i["program_name"] == "Fuerza base" for i in items)
    # el registro propio de un atleta (su "mis entrenamientos") no es programación del coach
    atleta_solo.post("/users/me/personal-sessions", json={"scheduled_date": str(LUNES)})
    assert all(i["athlete_id"] != atleta_solo.id for i in _entrenos(coach).json())


def test_cada_coach_ve_solo_lo_suyo(coach, atleta_de_coach, dueno_de_box):
    _dia_de_atleta(coach, atleta_de_coach, LUNES)
    assert len(_entrenos(coach).json()) == 1
    assert _entrenos(dueno_de_box).json() == []


def test_rango_invalido_y_permisos(coach, atleta_de_coach, client):
    assert coach.get("/coach/trainings", params={"date_from": str(LUNES), "date_to": str(LUNES - timedelta(days=1))}).status_code == 400
    assert _entrenos(coach, LUNES, LUNES + timedelta(days=500)).status_code == 400
    assert coach.get("/coach/trainings").status_code == 422                      # faltan las fechas
    assert _entrenos(atleta_de_coach).status_code == 403                        # un atleta no ve esto
    assert client.get("/coach/trainings", params={"date_from": str(LUNES), "date_to": str(LUNES)}).status_code in (401, 403)
