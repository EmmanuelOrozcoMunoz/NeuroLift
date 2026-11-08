"""El atleta ve a qué grupos pertenece (se muestra en su cuenta)."""
from backend.tests.test_asignar_plan import grupo, plantilla, _asignar  # noqa: F401  (fixtures)


def test_el_atleta_ve_sus_grupos_y_nada_mas(client, coach, grupo, atleta_solo):
    g, ana, _ = grupo
    r = ana.get("/users/me/groups")
    assert r.status_code == 200
    assert [(x["id"], x["name"], x["has_cover_image"]) for x in r.json()] == [(g["id"], g["name"], False)]
    assert r.json()[0]["coach_name"] == "Coach Prueba"
    assert atleta_solo.get("/users/me/groups").json() == []


def test_la_portada_de_un_grupo_ajeno_o_sin_portada_no_se_sirve(client, coach, grupo, atleta_solo):
    g, ana, _ = grupo
    assert atleta_solo.get(f"/users/me/groups/{g['id']}/cover").status_code == 404   # no es suyo
    assert ana.get(f"/users/me/groups/{g['id']}/cover", follow_redirects=False).status_code == 404   # sin portada
