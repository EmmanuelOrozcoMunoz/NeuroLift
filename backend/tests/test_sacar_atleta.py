"""Sacar a un atleta de la cuenta de su coach sin borrarlo (cambio de entrenador)."""
from datetime import date

from backend.tests.conftest import PASSWORD, _email, _login


def _con_grupo(coach, atleta):
    grupo = coach.post("/groups/", json={"name": "Grupo", "athlete_ids": [atleta.id]}).json()["id"]
    r = coach.post(f"/groups/{grupo}/days", json={"date": str(date.today())})
    assert r.status_code == 200, r.text
    return grupo


def test_el_coach_saca_al_atleta_y_este_vuelve_a_ser_un_atleta_solo(coach, atleta_de_coach):
    grupo = _con_grupo(coach, atleta_de_coach)
    assert len(atleta_de_coach.get(f"/users/{atleta_de_coach.id}/mesocycles/").json()) == 1

    r = coach.post(f"/boxes/me/athletes/{atleta_de_coach.id}/release")
    assert r.status_code == 200, r.text

    # ya no es del coach: ni en su lista, ni en su grupo
    assert atleta_de_coach.id not in [a["id"] for a in coach.get("/users/athletes").json()]
    assert coach.get(f"/groups/{grupo}").json()["members"] == []
    # la cuenta sigue ahí, ahora como atleta solo, y conserva su programa
    yo = atleta_de_coach.get("/auth/me").json()
    assert yo["box"]["kind"] == "athlete" and yo["coach_id"] is None
    meso = atleta_de_coach.get(f"/users/{atleta_de_coach.id}/mesocycles/").json()
    assert len(meso) == 1 and meso[0]["group_id"] is None
    # el coach ya no puede ver sus datos
    assert coach.get(f"/users/{atleta_de_coach.id}/mesocycles/").status_code in (403, 404)


def test_sacar_al_atleta_eliminando_lo_que_le_programo_el_coach(coach, atleta_de_coach):
    _con_grupo(coach, atleta_de_coach)
    r = coach.post(f"/boxes/me/athletes/{atleta_de_coach.id}/release", params={"programas": "eliminar"})
    assert r.status_code == 200, r.text
    assert atleta_de_coach.get(f"/users/{atleta_de_coach.id}/mesocycles/").json() == []
    assert atleta_de_coach.get("/auth/me").json()["box"]["kind"] == "athlete"


def test_despues_de_salir_se_une_al_codigo_de_otro_coach(client, coach, atleta_de_coach):
    assert coach.post(f"/boxes/me/athletes/{atleta_de_coach.id}/release").status_code == 200
    otro_email = _email("otro")
    client.post("/boxes/register-coach", json={"full_name": "Otro Coach", "email": otro_email, "password": PASSWORD})
    otro = _login(client, otro_email)
    codigo = otro.get("/boxes/me").json()["invite_code"]

    r = atleta_de_coach.post("/boxes/join", json={"invite_code": codigo})
    assert r.status_code == 200, r.text
    assert atleta_de_coach.id in [a["id"] for a in otro.get("/users/athletes").json()]


def test_un_coach_no_saca_a_atletas_ajenos_ni_un_atleta_puede_hacerlo(client, coach, atleta_de_coach, atleta_solo):
    otro_email = _email("intruso")
    client.post("/boxes/register-coach", json={"full_name": "Intruso", "email": otro_email, "password": PASSWORD})
    intruso = _login(client, otro_email)
    assert intruso.post(f"/boxes/me/athletes/{atleta_de_coach.id}/release").status_code == 404
    assert atleta_de_coach.post(f"/boxes/me/athletes/{atleta_de_coach.id}/release").status_code == 403
    # sigue donde estaba
    assert atleta_de_coach.get("/auth/me").json()["coach_id"] == coach.id
