"""Edición masiva de un ejercicio en un programa de grupo (añadir, actualizar, eliminar)."""
from datetime import date

import uuid

import pytest

HOY = date.today()


def _registrar_atleta(client, codigo, nombre):
    email = f"{nombre.lower()}-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/auth/register", json={"email": email, "full_name": nombre, "password": "password123", "invite_code": codigo})
    assert r.status_code == 200, r.text
    token = client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]
    from backend.tests.conftest import Cuenta
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    return Cuenta(client, email, token, me)


@pytest.fixture
def programa(client, coach, atleta_de_coach, codigo_coach):
    """Grupo con dos atletas y un programa de un día (hoy). Devuelve un dict con todo lo necesario."""
    otro = _registrar_atleta(client, codigo_coach, "Otro")
    grupo = coach.post("/groups/", json={"name": "Equipo", "athlete_ids": [atleta_de_coach.id, otro.id]}).json()
    creado = coach.post("/mesocycles/manual/group", json={
        "group_id": grupo["id"], "name": "Bloque", "discipline": "CrossFit",
        "start_date": str(HOY), "weeks_count": 1, "training_days": [HOY.weekday()],
    })
    assert creado.status_code == 200, creado.text
    base = {"program_name": "Bloque", "program_start_date": str(HOY), "scheduled_date": str(HOY)}
    return {"grupo": grupo["id"], "base": base, "atletas": [atleta_de_coach, otro]}


def _series(coach, cuenta, nombre):
    meso = next(m for m in coach.get(f"/users/{cuenta.id}/mesocycles/").json() if m["name"] == "Bloque")
    sesiones = coach.get(f"/mesocycles/{meso['id']}").json()["sessions"]
    return [s for ses in sesiones for s in ses["sets"] if s["exercise"]["name"] == nombre]


def _agregar(coach, p, **extra):
    r = coach.post(f"/groups/{p['grupo']}/sessions/bulk-add-exercise",
                   json={**p["base"], "exercise_name": "Back Squat", "prescribed_sets": 2, "prescribed_reps": 5, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def test_agregar_llega_a_todos_y_cada_atleta_recibe_su_porcentaje(coach, programa):
    a, b = programa["atletas"]
    a.post(f"/users/{a.id}/records/", json={"exercise_name": "Back Squat", "max_weight_kg": 100})
    b.post(f"/users/{b.id}/records/", json={"exercise_name": "Back Squat", "max_weight_kg": 60})

    resp = _agregar(coach, programa, prescribed_percentage=80)
    assert [r["status"] for r in resp["results"]] == ["añadido", "añadido"]
    assert {s["prescribed_weight"] for s in _series(coach, a, "Back Squat")} == {80}
    assert {s["prescribed_weight"] for s in _series(coach, b, "Back Squat")} == {47.5}  # 80 % de 60, a 2,5


def test_actualizar_cambia_series_y_conserva_o_borra_la_nota(coach, programa):
    a, b = programa["atletas"]
    _agregar(coach, programa, coach_note="Espalda neutra")
    ruta = f"/groups/{programa['grupo']}/sessions/bulk-update-exercise"
    cambio = {**programa["base"], "exercise_name": "Back Squat", "new_exercise_name": "Back Squat", "prescribed_reps": 3}

    # más series y sin mandar la nota: la existente se conserva y las series nuevas la heredan
    assert coach.put(ruta, json={**cambio, "prescribed_sets": 4}).status_code == 200
    for atleta in (a, b):
        series = _series(coach, atleta, "Back Squat")
        assert len(series) == 4 and all(s["prescribed_reps"] == 3 for s in series)
        assert all(s["coach_note"] == "Espalda neutra" for s in series)

    # menos series y con nota vacía: se borra en las que quedan
    assert coach.put(ruta, json={**cambio, "prescribed_sets": 1, "coach_note": ""}).status_code == 200
    for atleta in (a, b):
        series = _series(coach, atleta, "Back Squat")
        assert len(series) == 1 and series[0]["coach_note"] is None


def test_actualizar_puede_renombrar_el_ejercicio(coach, programa):
    a, _ = programa["atletas"]
    _agregar(coach, programa)
    r = coach.put(f"/groups/{programa['grupo']}/sessions/bulk-update-exercise", json={
        **programa["base"], "exercise_name": "Back Squat", "new_exercise_name": "Front Squat",
        "prescribed_sets": 2, "prescribed_reps": 5,
    })
    assert r.status_code == 200
    assert len(_series(coach, a, "Front Squat")) == 2 and _series(coach, a, "Back Squat") == []


def test_actualizar_y_eliminar_informan_a_quien_no_tenia_el_ejercicio(coach, programa):
    a, b = programa["atletas"]
    _agregar(coach, programa)
    # b pierde el ejercicio por su lado; el masivo debe decirlo y no fallar
    for s in _series(coach, b, "Back Squat"):
        assert coach.delete(f"/sets/{s['id']}").status_code == 200

    upd = coach.put(f"/groups/{programa['grupo']}/sessions/bulk-update-exercise", json={
        **programa["base"], "exercise_name": "Back Squat", "new_exercise_name": "Back Squat",
        "prescribed_sets": 2, "prescribed_reps": 8,
    }).json()
    assert sorted(r["status"] for r in upd["results"]) == ["actualizado", "no tenía ese ejercicio en esa fecha"]

    borr = coach.post(f"/groups/{programa['grupo']}/sessions/bulk-delete-exercise",
                      json={**programa["base"], "exercise_name": "Back Squat"}).json()
    assert sorted(r["status"] for r in borr["results"]) == ["eliminado", "no tenía ese ejercicio"]
    assert _series(coach, a, "Back Squat") == []


def test_una_fecha_sin_sesion_se_informa_por_atleta(coach, programa):
    base = {**programa["base"], "scheduled_date": "2001-01-01"}
    r = coach.post(f"/groups/{programa['grupo']}/sessions/bulk-add-exercise",
                   json={**base, "exercise_name": "Snatch", "prescribed_sets": 1, "prescribed_reps": 1})
    assert r.status_code == 200
    assert {x["status"] for x in r.json()["results"]} == {"sin sesión en esa fecha"}


def test_otro_coach_no_puede_editar_el_programa(client, programa):
    from backend.tests.conftest import _email, PASSWORD, _login
    email = _email("intruso")
    client.post("/boxes/register-coach", json={"full_name": "Intruso", "email": email, "password": PASSWORD})
    intruso = _login(client, email)
    r = intruso.post(f"/groups/{programa['grupo']}/sessions/bulk-add-exercise",
                     json={**programa["base"], "exercise_name": "Snatch", "prescribed_sets": 1, "prescribed_reps": 1})
    assert r.status_code in (403, 404)
