"""Una serie prescrita en % de 1RM se recalcula con la marca vigente mientras la sesión está
pendiente, y ese kg se GUARDA: al completar la sesión (o anotar la serie) queda escrito lo que el
atleta vio, no el kg viejo de cuando se generó con otras marcas."""
from datetime import date

import pytest

HOY = date.today()


def _marca(atleta, ejercicio, kg):
    r = atleta.post(f"/users/{atleta.id}/records/", json={"exercise_name": ejercicio, "max_weight_kg": kg})
    assert r.status_code == 200, r.text


@pytest.fixture
def sesion(coach, atleta_de_coach):
    """Sesión de hoy con Front Squat al 80% de su Back Squat y Power Clean al 80% de su Clean & Jerk."""
    _marca(atleta_de_coach, "Back Squat", 100)
    _marca(atleta_de_coach, "Clean & Jerk", 60)
    meso = coach.post("/mesocycles/manual", json={
        "user_id": atleta_de_coach.id, "name": "Base", "discipline": "CrossFit",
        "start_date": str(HOY), "weeks_count": 1, "training_days": [HOY.weekday()],
    }).json()
    sesion_id = coach.get(f"/mesocycles/{meso['mesocycle_id']}").json()["sessions"][0]["id"]
    for nombre, referencia, bloque in (("Front Squat", "Back Squat", "strength"), ("Power clean", "Clean & Jerk", "weightlifting")):
        r = coach.post(f"/sessions/{sesion_id}/sets/", json={
            "exercise_name": nombre, "prescribed_sets": 2, "prescribed_reps": 3,
            "prescribed_percentage": 80, "reference_exercise": referencia, "block": bloque,
        })
        assert r.status_code == 200, r.text
    return meso["mesocycle_id"], sesion_id


def _series(atleta, meso_id):
    sesiones = atleta.get(f"/mesocycles/{meso_id}").json()["sessions"]
    return {s["exercise"]["name"]: s for ses in sesiones for s in ses["sets"]}


def _estado(atleta, meso_id):
    return {nombre: s["prescribed_weight"] for nombre, s in _series(atleta, meso_id).items()}


def test_cada_porcentaje_se_calcula_con_la_marca_de_su_propio_ejercicio(atleta_de_coach, sesion):
    meso_id, _ = sesion
    assert _estado(atleta_de_coach, meso_id) == {"Front Squat": 80, "Power clean": 47.5}


def test_si_cambia_la_marca_la_sesion_pendiente_se_actualiza_y_queda_guardada(coach, atleta_de_coach, sesion):
    meso_id, _ = sesion
    _marca(atleta_de_coach, "Back Squat", 150)
    assert _estado(atleta_de_coach, meso_id)["Front Squat"] == 120
    # el coach lo ve igual, y sigue así al volver a leer: está guardado, no solo calculado al vuelo
    assert _estado(coach, meso_id)["Front Squat"] == 120
    assert _estado(atleta_de_coach, meso_id)["Front Squat"] == 120


def test_al_completar_la_sesion_el_kg_que_vio_el_atleta_queda_escrito(coach, atleta_de_coach, sesion):
    """El caso real: la sesión se generó con marcas equivocadas, el atleta corrigió sus marcas,
    entrenó con los kg correctos y, al completar, la tarjeta volvía a mostrar los kg viejos."""
    meso_id, sesion_id = sesion
    _marca(atleta_de_coach, "Back Squat", 125)
    _marca(atleta_de_coach, "Clean & Jerk", 88)
    # el atleta abre su sesión (ve los kg con las marcas buenas) y termina sin que nadie más la haya leído
    assert atleta_de_coach.post(f"/sessions/{sesion_id}/complete").status_code == 200
    assert _estado(atleta_de_coach, meso_id) == {"Front Squat": 100, "Power clean": 70}

    # una vez completada ya no se mueve aunque cambien las marcas
    _marca(atleta_de_coach, "Back Squat", 200)
    assert _estado(atleta_de_coach, meso_id) == {"Front Squat": 100, "Power clean": 70}


def test_una_serie_ya_anotada_no_cambia_si_despues_cambia_la_marca(atleta_de_coach, sesion):
    meso_id, _ = sesion
    serie = _series(atleta_de_coach, meso_id)["Front Squat"]
    r = atleta_de_coach.put(f"/sets/{serie['id']}/log", json={"actual_reps": 3, "actual_weight": 80})
    assert r.status_code == 200, r.text

    _marca(atleta_de_coach, "Back Squat", 150)
    _marca(atleta_de_coach, "Clean & Jerk", 100)
    # la anotada conserva su prescripción; la que sigue pendiente sí se actualiza
    assert _estado(atleta_de_coach, meso_id) == {"Front Squat": 80, "Power clean": 80}


def test_si_se_borra_la_marca_se_conserva_el_kg_que_tenia(atleta_de_coach, sesion):
    meso_id, _ = sesion
    marcas = atleta_de_coach.get(f"/users/{atleta_de_coach.id}/records/").json()
    back = next(m for m in marcas if m["exercise_name"] == "Back Squat")
    assert atleta_de_coach.delete(f"/users/{atleta_de_coach.id}/records/{back['id']}").status_code == 200
    assert _estado(atleta_de_coach, meso_id)["Front Squat"] == 80
