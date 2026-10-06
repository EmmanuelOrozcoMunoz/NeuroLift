"""PUT /sessions/{id}/log-sets: registrar varias series de una sesión en una sola petición."""
from datetime import date

import pytest

HOY = date.today()


@pytest.fixture
def sesion(coach, atleta_de_coach):
    meso = coach.post("/mesocycles/manual", json={
        "user_id": atleta_de_coach.id, "name": "Base", "discipline": "CrossFit",
        "start_date": str(HOY), "weeks_count": 1, "training_days": [HOY.weekday()],
    }).json()
    sesion_id = coach.get(f"/mesocycles/{meso['mesocycle_id']}").json()["sessions"][0]["id"]
    for _ in range(3):  # cada llamada agrega UNA serie
        r = coach.post(f"/sessions/{sesion_id}/sets/", json={
            "exercise_name": "Back Squat", "prescribed_reps": 5, "prescribed_weight": 80,
        })
        assert r.status_code == 200, r.text
    return meso["mesocycle_id"], sesion_id


def _series(cuenta, meso_id):
    sesion = cuenta.get(f"/mesocycles/{meso_id}").json()["sessions"][0]
    return sorted(sesion["sets"], key=lambda s: s["set_order"])


def test_registra_todas_las_series_de_golpe_y_se_puede_deshacer(atleta_de_coach, sesion):
    meso_id, sesion_id = sesion
    series = _series(atleta_de_coach, meso_id)
    assert len(series) == 3

    r = atleta_de_coach.put(f"/sessions/{sesion_id}/log-sets", json={
        "sets": [{"set_id": s["id"], "actual_reps": 5, "actual_weight": 80} for s in series],
    })
    assert r.status_code == 200, r.text
    assert [(s["actual_reps"], s["actual_weight"]) for s in _series(atleta_de_coach, meso_id)] == [(5, 80)] * 3

    r = atleta_de_coach.put(f"/sessions/{sesion_id}/log-sets", json={
        "sets": [{"set_id": s["id"], "actual_reps": None, "actual_weight": None} for s in series],
    })
    assert r.status_code == 200, r.text
    assert [(s["actual_reps"], s["actual_weight"]) for s in _series(atleta_de_coach, meso_id)] == [(None, None)] * 3


def test_su_coach_tambien_puede_registrar(coach, atleta_de_coach, sesion):
    meso_id, sesion_id = sesion
    series = _series(atleta_de_coach, meso_id)
    r = coach.put(f"/sessions/{sesion_id}/log-sets", json={"sets": [{"set_id": series[0]["id"], "actual_reps": 4, "actual_weight": 82.5}]})
    assert r.status_code == 200, r.text
    assert _series(atleta_de_coach, meso_id)[0]["actual_weight"] == 82.5


def test_una_serie_ajena_a_la_sesion_rechaza_todo_el_lote(atleta_de_coach, atleta_solo, sesion):
    meso_id, sesion_id = sesion
    series = _series(atleta_de_coach, meso_id)
    r = atleta_de_coach.put(f"/sessions/{sesion_id}/log-sets", json={"sets": [
        {"set_id": series[0]["id"], "actual_reps": 5, "actual_weight": 80},
        {"set_id": "00000000-0000-0000-0000-000000000000", "actual_reps": 5, "actual_weight": 80},
    ]})
    assert r.status_code == 400
    # nada se guardó (ni siquiera la serie válida)
    assert _series(atleta_de_coach, meso_id)[0]["actual_reps"] is None


def test_otro_atleta_no_puede_registrar_en_una_sesion_ajena(atleta_solo, atleta_de_coach, sesion):
    meso_id, sesion_id = sesion
    series = _series(atleta_de_coach, meso_id)
    r = atleta_solo.put(f"/sessions/{sesion_id}/log-sets", json={"sets": [{"set_id": series[0]["id"], "actual_reps": 5, "actual_weight": 80}]})
    assert r.status_code in (403, 404)
    assert _series(atleta_de_coach, meso_id)[0]["actual_reps"] is None


@pytest.mark.parametrize("cuerpo", [
    {"sets": []},
    {"sets": [{"set_id": "00000000-0000-0000-0000-000000000000", "actual_reps": 201}]},
    {"sets": [{"set_id": "00000000-0000-0000-0000-000000000000", "actual_weight": -1}]},
])
def test_valida_el_cuerpo(atleta_de_coach, sesion, cuerpo):
    _, sesion_id = sesion
    assert atleta_de_coach.put(f"/sessions/{sesion_id}/log-sets", json=cuerpo).status_code == 422
