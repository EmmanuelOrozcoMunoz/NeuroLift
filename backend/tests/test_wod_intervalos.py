"""WOD por intervalos: el coach fija cuántos son, el atleta anota el tiempo de cada uno y gana el menor total."""
from backend.tests.test_asignar_plan import grupo, plantilla, _asignar  # noqa: F401  (fixtures)
from backend.tests.test_entrenos_del_coach import LUNES, _dia_de_grupo, _entrenos, _resultados, _sesiones


def _con_intervalos(coach, g, cuantos=3):
    dia = _dia_de_grupo(coach, g, LUNES)
    r = coach.post(f"/groups/{g['id']}/sessions/bulk-set-wod-format", json={
        "program_name": dia["program_name"], "program_start_date": dia["program_start_date"],
        "scheduled_date": dia["scheduled_date"], "wod_format": "intervals", "intervals": cuantos,
    })
    assert r.status_code == 200, r.text
    return next(i for i in _entrenos(coach).json() if i["kind"] == "group")["session_id"]


def _sesion(atleta):
    return next(s for s in _sesiones(atleta) if s["scheduled_date"] == str(LUNES))


def _terminar(atleta, tiempos):
    return atleta.post(f"/sessions/{_sesion(atleta)['id']}/complete", json={"wod_interval_times": tiempos})


def test_el_coach_tiene_que_decir_cuantos_intervalos(coach, grupo):
    g, _, _ = grupo
    dia = _dia_de_grupo(coach, g, LUNES)
    r = coach.post(f"/groups/{g['id']}/sessions/bulk-set-wod-format", json={
        "program_name": dia["program_name"], "program_start_date": dia["program_start_date"],
        "scheduled_date": dia["scheduled_date"], "wod_format": "intervals",
    })
    assert r.status_code == 422


def test_el_total_de_los_intervalos_ordena_y_gana_el_menor(coach, grupo):
    g, ana, beto = grupo
    referencia = _con_intervalos(coach, g)
    assert _terminar(ana, [60, 70, 80]).status_code == 200      # 3:30
    assert _terminar(beto, [50, 60, 65]).status_code == 200     # 2:55 -> mejor

    sesion = _sesion(beto)
    assert sesion["wod_format"] == "intervals" and sesion["wod_intervals"] == 3
    assert sesion["wod_interval_times"] == [50, 60, 65] and sesion["wod_time_seconds"] == 175

    cuerpo = _resultados(coach, referencia).json()
    assert cuerpo["wod_format"] == "intervals"
    assert [(f["full_name"], f["rank"]) for f in cuerpo["rows"]] == [("Beto", 1), ("Ana", 2)] or \
        [f["rank"] for f in cuerpo["rows"]] == [1, 2]
    assert "Intervalos" in cuerpo["rows"][0]["score_label"] and "2:55" in cuerpo["rows"][0]["score_label"]


def test_hay_que_anotar_todos_los_intervalos(coach, grupo):
    g, ana, _ = grupo
    _con_intervalos(coach, g, cuantos=3)
    r = _terminar(ana, [60, 70])
    assert r.status_code == 400 and "3 intervalos" in r.json()["detail"]
    assert _sesion(ana)["status"] == "pending"                   # no quedó terminada a medias
    assert _terminar(ana, [60, 0, 80]).status_code == 422        # un intervalo de 0 s no vale


def test_deshacer_borra_los_tiempos_de_los_intervalos(coach, grupo):
    g, ana, _ = grupo
    _con_intervalos(coach, g)
    _terminar(ana, [60, 70, 80])
    assert ana.post(f"/sessions/{_sesion(ana)['id']}/uncomplete").status_code == 200
    sesion = _sesion(ana)
    assert sesion["wod_interval_times"] is None and sesion["wod_time_seconds"] is None
