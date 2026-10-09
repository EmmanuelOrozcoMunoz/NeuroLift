"""PUT /plans/{id}/sessions/{id}/exercise: editar un ejercicio ya agregado a un día de un plan."""
import pytest

from backend.tests.conftest import PASSWORD, _email, _login


def _plan(coach):
    plan = coach.post("/plans/", json={
        "name": "Fuerza base", "description": "", "discipline": "CrossFit", "level": "Intermedio",
        "weeks_count": 1, "training_days": [0, 3],
    }).json()
    dia1, dia2 = coach.get(f"/plans/{plan['id']}").json()["sessions"][:2]
    return plan, dia1["id"], dia2["id"]


def _agregar(coach, plan_id, dia_id, nombre, **extra):
    cuerpo = {"exercise_name": nombre, "prescribed_sets": 3, "prescribed_reps": 5, "prescribed_percentage": 80,
              "reference_exercise": nombre, "block": "strength", **extra}
    r = coach.post(f"/plans/{plan_id}/sessions/{dia_id}/sets", json=cuerpo)
    assert r.status_code == 200, r.text


def _series(coach, plan_id, dia_id):
    sesion = next(s for s in coach.get(f"/plans/{plan_id}").json()["sessions"] if s["id"] == dia_id)
    return sorted(sesion["sets"], key=lambda s: s["set_order"])


def _editar(coach, plan_id, dia_id, actuales, **cambios):
    """`actuales` son las series que tiene hoy el ejercicio; `cambios` pisa cualquier campo del cuerpo."""
    cuerpo = {"set_ids": [s["id"] for s in actuales], "exercise_name": actuales[0]["exercise"]["name"],
              "prescribed_sets": len(actuales), "prescribed_reps": actuales[0]["prescribed_reps"], **cambios}
    return coach.put(f"/plans/{plan_id}/sessions/{dia_id}/exercise", json=cuerpo)


@pytest.fixture
def plan(coach):
    p, dia1, dia2 = _plan(coach)
    _agregar(coach, p["id"], dia1, "Back Squat", coach_note="Baja controlado")
    _agregar(coach, p["id"], dia1, "Snatch", block="weightlifting", prescribed_reps=2, prescribed_percentage=70)
    return p["id"], dia1, dia2


def _de(series, nombre):
    return [s for s in series if s["exercise"]["name"] == nombre]


def test_cambia_repeticiones_carga_rpe_y_nombre_en_una_peticion(coach, plan):
    plan_id, dia, _ = plan
    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    r = _editar(coach, plan_id, dia, squat, exercise_name="Front Squat", prescribed_reps=3,
                prescribed_percentage=85, reference_exercise="Back Squat", rpe=8)
    assert r.status_code == 200, r.text

    editado = _de(_series(coach, plan_id, dia), "Front Squat")
    assert len(editado) == 3
    assert {(s["prescribed_reps"], s["prescribed_percentage"], s["rpe"], s["reference_exercise"]) for s in editado} == {(3, 85, 8, "Back Squat")}
    assert _de(_series(coach, plan_id, dia), "Back Squat") == []
    # el otro ejercicio no se toca
    assert len(_de(_series(coach, plan_id, dia), "Snatch")) == 3


def test_menos_series_borra_las_ultimas(coach, plan):
    plan_id, dia, _ = plan
    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    assert _editar(coach, plan_id, dia, squat, prescribed_sets=2).status_code == 200
    quedan = _de(_series(coach, plan_id, dia), "Back Squat")
    assert [s["id"] for s in quedan] == [s["id"] for s in squat[:2]]


def test_mas_series_y_rampa_se_agregan_junto_al_ejercicio_sin_mover_a_los_demas(coach, plan):
    plan_id, dia, _ = plan
    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    rampa = [{"prescribed_reps": 5, "prescribed_percentage": 60}, {"prescribed_reps": 3, "prescribed_percentage": 70},
             {"prescribed_reps": 3, "prescribed_percentage": 80}, {"prescribed_reps": 1, "prescribed_percentage": 90},
             {"prescribed_reps": 1, "prescribed_percentage": 95}]
    assert _editar(coach, plan_id, dia, squat, series=rampa).status_code == 200

    todas = _series(coach, plan_id, dia)
    assert [s["exercise"]["name"] for s in todas] == ["Back Squat"] * 5 + ["Snatch"] * 3  # juntas, Snatch sigue después
    assert [(s["prescribed_reps"], s["prescribed_percentage"]) for s in todas[:5]] == [(5, 60), (3, 70), (3, 80), (1, 90), (1, 95)]
    assert [s["id"] for s in todas[:3]] == [s["id"] for s in squat]  # las existentes se reutilizan, no se recrean


def test_la_nota_se_conserva_si_no_se_manda_y_se_borra_con_cadena_vacia(coach, plan):
    plan_id, dia, _ = plan
    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    _editar(coach, plan_id, dia, squat, prescribed_reps=4)
    assert {s["coach_note"] for s in _de(_series(coach, plan_id, dia), "Back Squat")} == {"Baja controlado"}

    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    _editar(coach, plan_id, dia, squat, coach_note="Pausa abajo")
    assert {s["coach_note"] for s in _de(_series(coach, plan_id, dia), "Back Squat")} == {"Pausa abajo"}

    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    _editar(coach, plan_id, dia, squat, coach_note="")
    assert {s["coach_note"] for s in _de(_series(coach, plan_id, dia), "Back Squat")} <= {None, ""}


def test_el_bloque_cambia_solo_si_se_manda(coach, plan):
    plan_id, dia, _ = plan
    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    _editar(coach, plan_id, dia, squat, prescribed_reps=4)
    assert {s["block"] for s in _de(_series(coach, plan_id, dia), "Back Squat")} == {"strength"}

    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    _editar(coach, plan_id, dia, squat, block="warmup")
    assert {s["block"] for s in _de(_series(coach, plan_id, dia), "Back Squat")} == {"warmup"}


def test_series_de_otro_dia_se_rechazan_y_no_cambia_nada(coach, plan):
    plan_id, dia1, dia2 = plan
    _agregar(coach, plan_id, dia2, "Deadlift")
    ajeno = _de(_series(coach, plan_id, dia2), "Deadlift")
    squat = _de(_series(coach, plan_id, dia1), "Back Squat")

    r = coach.put(f"/plans/{plan_id}/sessions/{dia1}/exercise", json={
        "set_ids": [s["id"] for s in squat] + [ajeno[0]["id"]], "exercise_name": "Hackeado",
        "prescribed_sets": 4, "prescribed_reps": 9, "prescribed_percentage": 99,
    })
    assert r.status_code == 404
    assert [(s["exercise"]["name"], s["prescribed_reps"]) for s in _series(coach, plan_id, dia2)] == [("Deadlift", 5)] * 3
    assert {s["exercise"]["name"] for s in _series(coach, plan_id, dia1)} == {"Back Squat", "Snatch"}


def test_otro_coach_no_puede_editar_un_plan_ajeno(client, plan, coach):
    plan_id, dia, _ = plan
    email = _email("otrocoach")
    assert client.post("/boxes/register-coach", json={"full_name": "Otro", "email": email, "password": PASSWORD}).status_code == 200
    otro = _login(client, email)
    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    assert _editar(otro, plan_id, dia, squat, prescribed_reps=1).status_code in (403, 404)
    assert {s["prescribed_reps"] for s in _de(_series(coach, plan_id, dia), "Back Squat")} == {5}


def test_un_atleta_no_puede_editar_planes(atleta_de_coach, plan, coach):
    plan_id, dia, _ = plan
    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    assert _editar(atleta_de_coach, plan_id, dia, squat, prescribed_reps=1).status_code == 403


@pytest.mark.parametrize("cambio", [
    {"set_ids": []},
    {"prescribed_reps": 0},
    {"prescribed_percentage": 500},
    {"exercise_name": ""},
])
def test_valida_el_cuerpo(coach, plan, cambio):
    plan_id, dia, _ = plan
    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    assert _editar(coach, plan_id, dia, squat, **cambio).status_code == 422


def test_el_atleta_recibe_el_ejercicio_editado_con_sus_kg(coach, atleta_de_coach, plan):
    """Lo editado es lo que se adquiere: el % nuevo se resuelve con las marcas del atleta."""
    plan_id, dia, _ = plan
    r = atleta_de_coach.post(f"/users/{atleta_de_coach.id}/records/", json={"exercise_name": "Back Squat", "max_weight_kg": 100})
    assert r.status_code == 200, r.text
    squat = _de(_series(coach, plan_id, dia), "Back Squat")
    assert _editar(coach, plan_id, dia, squat, prescribed_percentage=90, prescribed_reps=3).status_code == 200
    assert coach.put(f"/plans/{plan_id}/publish", json={"is_published": True}).status_code == 200

    r = atleta_de_coach.post(f"/plans/{plan_id}/acquire", json={"start_date": "2030-01-07"})
    assert r.status_code == 200, r.text
    meso = atleta_de_coach.get(f"/mesocycles/{r.json()['mesocycle_id']}").json()
    series = [s for ses in meso["sessions"] for s in ses["sets"] if s["exercise"]["name"] == "Back Squat"]
    assert {(s["prescribed_reps"], s["prescribed_percentage"], s["prescribed_weight"]) for s in series} == {(3, 90, 90)}
