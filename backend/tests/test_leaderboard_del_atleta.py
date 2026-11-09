"""El atleta ve el leaderboard de cada entreno de SU grupo: solo quienes lo terminaron y aceptan aparecer."""
from backend.tests.test_asignar_plan import grupo, plantilla, _asignar, _atleta  # noqa: F401  (fixtures y ayudas)
from backend.tests.test_entrenos_del_coach import LUNES, _con_wod, _dia_de_atleta, _entrenos, _sesiones, _terminar


def _sesion_de(atleta):
    return next(s for s in _sesiones(atleta) if s["scheduled_date"] == str(LUNES))


def _leaderboard(atleta):
    return atleta.get(f"/sessions/{_sesion_de(atleta)['id']}/leaderboard")


def test_el_atleta_ve_a_sus_companeros_ordenados_y_sin_los_pendientes(client, coach, codigo_coach, grupo):
    g, ana, beto = grupo
    carla = _atleta(client, codigo_coach, "Carla")
    assert coach.post(f"/groups/{g['id']}/members", json={"athlete_ids": [carla.id]}).status_code == 200
    _con_wod(coach, g)
    _terminar(ana, LUNES, 600)
    _terminar(beto, LUNES, 540)      # mejor; Carla no lo ha terminado

    r = _leaderboard(ana)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["kind"] == "group" and cuerpo["wod_format"] == "for_time"
    assert [(f["full_name"], f["rank"]) for f in cuerpo["rows"]] == [("Beto", 1), ("Ana", 2)]   # Carla (pendiente) no sale
    assert (cuerpo["total"], cuerpo["completed"]) == (2, 2)


def test_quien_apaga_el_interruptor_del_perfil_no_aparece_para_los_demas(client, coach, grupo):
    g, ana, beto = grupo
    _con_wod(coach, g)
    _terminar(ana, LUNES, 600)
    _terminar(beto, LUNES, 540)
    assert beto.put("/users/me/preferences", json={"show_in_ranking": False}).status_code == 200

    de_ana = [f["full_name"] for f in _leaderboard(ana).json()["rows"]]
    assert de_ana == ["Ana"]
    de_beto = [f["full_name"] for f in _leaderboard(beto).json()["rows"]]
    assert de_beto == ["Beto", "Ana"]        # él sí se ve a sí mismo (y va primero: menos tiempo)


def test_un_entreno_ajeno_o_no_grupal_no_se_ve(client, coach, grupo, atleta_de_coach, atleta_solo):
    g, ana, beto = grupo
    _con_wod(coach, g)
    sesion_de_ana = _sesion_de(ana)
    assert ana.get(f"/sessions/{sesion_de_ana['id']}/leaderboard").status_code == 200     # la suya, sí
    # nadie más (ni un compañero del grupo ni un atleta de fuera) puede pedirlo con el id de OTRO: solo con el suyo
    assert beto.get(f"/sessions/{sesion_de_ana['id']}/leaderboard").status_code == 404
    assert atleta_de_coach.get(f"/sessions/{sesion_de_ana['id']}/leaderboard").status_code == 404
    # un día personalizado (sin grupo) no tiene compañeros
    _dia_de_atleta(coach, atleta_de_coach, LUNES)
    propia = next(s for s in _sesiones(atleta_de_coach) if s["scheduled_date"] == str(LUNES))
    assert atleta_de_coach.get(f"/sessions/{propia['id']}/leaderboard").status_code == 404


def test_el_mesociclo_dice_de_que_grupo_es(coach, grupo):
    g, ana, _ = grupo
    _con_wod(coach, g)
    meso = ana.get(f"/users/{ana.id}/mesocycles/").json()[0]
    assert ana.get(f"/mesocycles/{meso['id']}").json()["group_id"] == g["id"]
