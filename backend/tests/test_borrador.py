"""Borrador: lo que arma la IA para un atleta queda oculto para él hasta que su coach lo publique.
El coach lo ve y lo edita con normalidad; ningún otro coach ni el propio atleta pueden publicarlo."""
from datetime import date

from backend.tests.test_ia_mesociclos import HOY, _pedir, gemini  # noqa: F401  (fixture)


def _meso_ia(coach, atleta):
    return next(m for m in coach.get(f"/users/{atleta.id}/mesocycles/").json() if m["name"] == "Bloque IA")


def _generar(coach, atleta):
    r = _pedir(coach, atleta)
    assert r.status_code == 200, r.text
    meso = _meso_ia(coach, atleta)
    detalle = coach.get(f"/mesocycles/{meso['id']}").json()
    sesion = detalle["sessions"][0]
    return meso, sesion, sesion["sets"][0]


def test_lo_que_genera_la_ia_para_un_atleta_queda_en_borrador(coach, atleta_de_coach, gemini):
    meso, _, _ = _generar(coach, atleta_de_coach)
    assert meso["is_draft"] is True
    assert coach.get(f"/mesocycles/{meso['id']}").json()["is_draft"] is True


def test_el_atleta_no_ve_el_borrador_ni_en_su_lista_ni_por_id(coach, atleta_de_coach, gemini):
    meso, _, _ = _generar(coach, atleta_de_coach)
    mios = atleta_de_coach.get(f"/users/{atleta_de_coach.id}/mesocycles/").json()
    assert all(m["id"] != meso["id"] for m in mios)
    assert atleta_de_coach.get(f"/mesocycles/{meso['id']}").status_code == 404
    # el coach sí sigue viéndolo en la lista del atleta
    assert any(m["id"] == meso["id"] for m in coach.get(f"/users/{atleta_de_coach.id}/mesocycles/").json())


def test_el_atleta_no_puede_registrar_nada_en_un_borrador(coach, atleta_de_coach, gemini):
    _, sesion, serie = _generar(coach, atleta_de_coach)
    a = atleta_de_coach
    assert a.put(f"/sets/{serie['id']}/log", json={"actual_reps": 5, "actual_weight": 60}).status_code == 404
    assert a.put(f"/sessions/{sesion['id']}/log-sets", json={"sets": [{"set_id": serie["id"], "actual_reps": 5, "actual_weight": 60}]}).status_code == 404
    assert a.post(f"/sessions/{sesion['id']}/complete").status_code == 404
    assert a.post(f"/sessions/{sesion['id']}/uncomplete").status_code == 404
    assert a.post(f"/sessions/{sesion['id']}/adapt", json={"available_minutes": 45}).status_code == 404


def test_el_coach_puede_editar_y_registrar_en_el_borrador(coach, atleta_de_coach, gemini):
    _, sesion, serie = _generar(coach, atleta_de_coach)
    assert coach.put(f"/sessions/{sesion['id']}/meta", json={"warmup_notes": "Movilidad"}).status_code == 200
    assert coach.put(f"/sets/{serie['id']}/log", json={"actual_reps": 5, "actual_weight": 60}).status_code == 200


def test_publicar_lo_deja_visible_para_el_atleta(coach, atleta_de_coach, gemini):
    meso, _, serie = _generar(coach, atleta_de_coach)
    r = coach.post(f"/mesocycles/{meso['id']}/publish")
    assert r.status_code == 200, r.text

    assert _meso_ia(coach, atleta_de_coach)["is_draft"] is False
    assert any(m["id"] == meso["id"] for m in atleta_de_coach.get(f"/users/{atleta_de_coach.id}/mesocycles/").json())
    assert atleta_de_coach.get(f"/mesocycles/{meso['id']}").status_code == 200
    assert atleta_de_coach.put(f"/sets/{serie['id']}/log", json={"actual_reps": 5, "actual_weight": 60}).status_code == 200


def test_publicar_dos_veces_no_falla(coach, atleta_de_coach, gemini):
    meso, _, _ = _generar(coach, atleta_de_coach)
    assert coach.post(f"/mesocycles/{meso['id']}/publish").status_code == 200
    assert coach.post(f"/mesocycles/{meso['id']}/publish").status_code == 200


def test_ni_el_atleta_ni_otro_coach_pueden_publicar(coach, atleta_de_coach, dueno_de_box, gemini):
    meso, _, _ = _generar(coach, atleta_de_coach)
    assert atleta_de_coach.post(f"/mesocycles/{meso['id']}/publish").status_code == 403
    assert dueno_de_box.post(f"/mesocycles/{meso['id']}/publish").status_code in (403, 404)
    assert _meso_ia(coach, atleta_de_coach)["is_draft"] is True


def test_publicar_un_mesociclo_inexistente_da_404(coach):
    assert coach.post("/mesocycles/00000000-0000-0000-0000-000000000000/publish").status_code == 404


def test_un_mesociclo_manual_no_es_borrador(coach, atleta_de_coach):
    r = coach.post("/mesocycles/manual", json={
        "user_id": atleta_de_coach.id, "name": "Manual", "discipline": "CrossFit",
        "start_date": str(date.today()), "weeks_count": 1, "training_days": [0],
    })
    assert r.status_code == 200, r.text
    meso = next(m for m in atleta_de_coach.get(f"/users/{atleta_de_coach.id}/mesocycles/").json() if m["name"] == "Manual")
    assert meso["is_draft"] is False
