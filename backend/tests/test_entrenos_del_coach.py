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
    assert item["completed_names"] == [ana.datos["full_name"]]     # y se sabe quién
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


# ------------------------------------------------------------------ cómo quedó un entreno entre sus miembros

def _resultados(cuenta, session_id):
    return cuenta.get(f"/coach/trainings/{session_id}/results")


def _con_wod(coach, g, fecha=None):
    """Un día de grupo con un WOD 'for time'; devuelve la sesión de referencia del entreno."""
    dia = _dia_de_grupo(coach, g, fecha or LUNES)
    coach.post(f"/groups/{g['id']}/sessions/bulk-set-wod-format", json={
        "program_name": dia["program_name"], "program_start_date": dia["program_start_date"],
        "scheduled_date": dia["scheduled_date"], "wod_format": "for_time", "time_cap_seconds": 900,
    })
    return next(i for i in _entrenos(coach).json() if i["kind"] == "group")["session_id"]


def _terminar(atleta, fecha, segundos=None):
    sesion = next(s for s in _sesiones(atleta) if s["scheduled_date"] == str(fecha))
    cuerpo = {"wod_time_seconds": segundos} if segundos else None
    r = atleta.post(f"/sessions/{sesion['id']}/complete", **({"json": cuerpo} if cuerpo else {}))
    assert r.status_code == 200, r.text


def test_el_ranking_de_un_wod_ordena_por_resultado_y_deja_al_final_a_los_pendientes(client, coach, codigo_coach, grupo):
    g, ana, beto = grupo
    carla = _atleta(client, codigo_coach, "Carla")
    assert coach.post(f"/groups/{g['id']}/members", json={"athlete_ids": [carla.id]}).status_code == 200
    referencia = _con_wod(coach, g)
    _terminar(ana, LUNES, 600)      # 10:00
    _terminar(beto, LUNES, 540)     # 9:00 -> mejor (for time: menos es mejor)

    r = _resultados(coach, referencia)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["kind"] == "group" and cuerpo["title"] == "Mañanas" and cuerpo["date"] == str(LUNES)
    assert (cuerpo["wod_format"], cuerpo["time_cap_seconds"]) == ("for_time", 900)
    assert (cuerpo["total"], cuerpo["completed"]) == (3, 2)
    filas = cuerpo["rows"]
    assert [(f["full_name"], f["rank"], f["completed"]) for f in filas] == [
        ("Beto", 1, True), ("Ana", 2, True), ("Carla", None, False)
    ]
    assert filas[0]["score_label"] and filas[2]["score_label"] is None and filas[0]["completed_at"] is not None


def test_un_wod_terminado_sin_resultado_no_tiene_posicion_pero_cuenta_como_terminado(coach, grupo):
    g, ana, beto = grupo
    referencia = _con_wod(coach, g)
    _terminar(ana, LUNES, 600)
    _terminar(beto, LUNES)                 # lo terminó pero no reportó tiempo
    filas = _resultados(coach, referencia).json()["rows"]
    assert [(f["full_name"], f["rank"]) for f in filas] == [("Ana", 1), ("Beto", None)]
    assert all(f["completed"] for f in filas)


def test_sin_wod_no_hay_posiciones_solo_quien_lo_termino_por_hora_y_luego_los_pendientes(coach, grupo):
    g, ana, beto = grupo
    _dia_de_grupo(coach, g, LUNES)
    referencia = _entrenos(coach).json()[0]["session_id"]
    _terminar(beto, LUNES)
    cuerpo = _resultados(coach, referencia).json()
    assert cuerpo["wod_format"] is None and cuerpo["wod_name"] is None
    assert [(f["full_name"], f["completed"], f["rank"]) for f in cuerpo["rows"]] == [("Beto", True, None), ("Ana", False, None)]
    assert (cuerpo["total"], cuerpo["completed"]) == (2, 1)


def test_el_resultado_de_un_entreno_personalizado_es_una_sola_fila(coach, atleta_de_coach):
    dia = _dia_de_atleta(coach, atleta_de_coach, LUNES)
    cuerpo = _resultados(coach, dia["session_id"]).json()
    assert cuerpo["kind"] == "athlete" and cuerpo["title"] == "Atleta Prueba"
    assert [(f["full_name"], f["completed"]) for f in cuerpo["rows"]] == [("Atleta Prueba", False)]
    atleta_de_coach.post(f"/sessions/{dia['session_id']}/complete")
    cuerpo = _resultados(coach, dia["session_id"]).json()
    assert (cuerpo["total"], cuerpo["completed"]) == (1, 1) and cuerpo["rows"][0]["completed"] is True


def test_los_resultados_cuentan_las_series_marcadas_del_atleta(coach, atleta_de_coach):
    dia = _dia_de_atleta(coach, atleta_de_coach, LUNES)
    for _ in range(2):      # cada llamada agrega UNA serie
        coach.post(f"/sessions/{dia['session_id']}/sets/", json={
            "exercise_name": "Back Squat", "prescribed_sets": 1, "prescribed_reps": 5, "block": "strength",
        })
    serie = coach.get(f"/mesocycles/{dia['mesocycle_id']}").json()["sessions"][0]["sets"][0]
    assert atleta_de_coach.put(f"/sets/{serie['id']}/log", json={"actual_reps": 5, "actual_weight": 60}).status_code == 200
    fila = _resultados(coach, dia["session_id"]).json()["rows"][0]
    assert (fila["sets_logged"], fila["sets_total"]) == (1, 2)


def test_resultados_permisos_y_entrenos_que_no_existen(coach, grupo, dueno_de_box, atleta_de_coach):
    import uuid

    g, ana, _ = grupo
    referencia = _con_wod(coach, g)
    assert _resultados(dueno_de_box, referencia).status_code in (403, 404)       # otro coach
    assert _resultados(ana, referencia).status_code == 403                       # un atleta no ve esto
    assert _resultados(coach, str(uuid.uuid4())).status_code == 404
    propio = ana.post("/users/me/personal-sessions", json={"scheduled_date": str(LUNES)}).json()
    assert _resultados(coach, propio["id"]).status_code == 404                   # el registro propio no es un entreno del coach
