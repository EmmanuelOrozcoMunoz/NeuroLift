"""Nota del coach por ejercicio: se guarda, se edita sin borrarse y viaja en las copias."""
from datetime import date

NOTA = "Codos arriba en la recepción. Si duele el hombro, baja el peso."


def _sesion_del_atleta(coach, atleta):
    """Crea un mesociclo manual (1 semana, todos los días) y devuelve (meso_id, sesion_id)."""
    r = coach.post(
        "/mesocycles/manual",
        json={
            "user_id": atleta.id,
            "name": "Bloque de prueba",
            "discipline": "CrossFit",
            "start_date": str(date.today()),
            "weeks_count": 1,
            "training_days": [0, 1, 2, 3, 4, 5, 6],
        },
    )
    assert r.status_code == 200, r.text
    meso_id = r.json()["mesocycle_id"]
    sesiones = coach.get(f"/mesocycles/{meso_id}").json()["sessions"]
    return meso_id, sorted(sesiones, key=lambda s: s["scheduled_date"])[0]["id"]


def _series(cuenta, meso_id, sesion_id, ejercicio):
    sesiones = cuenta.get(f"/mesocycles/{meso_id}").json()["sessions"]
    sesion = next(s for s in sesiones if s["id"] == sesion_id)
    return [s for s in sesion["sets"] if s["exercise"]["name"] == ejercicio]


def _agregar(coach, sesion_id, veces=3, **extra):
    for _ in range(veces):
        r = coach.post(
            f"/sessions/{sesion_id}/sets/",
            json={"exercise_name": "Power Clean", "prescribed_reps": 3, "prescribed_weight": 70, **extra},
        )
        assert r.status_code == 200, r.text


def test_la_nota_queda_en_todas_las_series_y_el_atleta_la_ve(coach, atleta_de_coach):
    meso, sesion = _sesion_del_atleta(coach, atleta_de_coach)
    _agregar(coach, sesion, coach_note=NOTA)
    for quien in (coach, atleta_de_coach):
        series = _series(quien, meso, sesion, "Power Clean")
        assert len(series) == 3 and all(s["coach_note"] == NOTA for s in series)


def test_editar_sin_mandar_la_nota_no_la_borra_y_con_vacio_si(coach, atleta_de_coach):
    meso, sesion = _sesion_del_atleta(coach, atleta_de_coach)
    _agregar(coach, sesion, coach_note=NOTA)
    serie_id = _series(coach, meso, sesion, "Power Clean")[0]["id"]
    cuerpo = {"exercise_name": "Power Clean", "prescribed_reps": 4, "prescribed_weight": 72.5}

    assert coach.put(f"/sets/{serie_id}", json=cuerpo).status_code == 200
    assert _series(coach, meso, sesion, "Power Clean")[0]["coach_note"] == NOTA

    coach.put(f"/sets/{serie_id}", json={**cuerpo, "coach_note": ""})
    assert _series(coach, meso, sesion, "Power Clean")[0]["coach_note"] is None


def test_la_nota_se_limpia_y_tiene_tope(coach, atleta_de_coach):
    meso, sesion = _sesion_del_atleta(coach, atleta_de_coach)
    _agregar(coach, sesion, veces=1, coach_note="<script>alert(1)</script>Rodillas afuera")
    nota = _series(coach, meso, sesion, "Power Clean")[0]["coach_note"]
    assert "<script" not in nota and "Rodillas afuera" in nota

    larga = coach.post(
        f"/sessions/{sesion}/sets/", json={"exercise_name": "X", "prescribed_reps": 1, "coach_note": "a" * 501}
    )
    assert larga.status_code == 422


def test_el_atleta_no_puede_editar_lo_que_prescribio_el_coach(coach, atleta_de_coach):
    meso, sesion = _sesion_del_atleta(coach, atleta_de_coach)
    _agregar(coach, sesion, veces=1)
    serie_id = _series(coach, meso, sesion, "Power Clean")[0]["id"]
    r = atleta_de_coach.put(
        f"/sets/{serie_id}", json={"exercise_name": "Power Clean", "prescribed_reps": 3, "coach_note": "x"}
    )
    assert r.status_code == 403


def test_adquirir_un_plan_copia_la_nota_y_resuelve_el_porcentaje(coach, atleta_de_coach):
    atleta_de_coach.post("/users/%s/records/" % atleta_de_coach.id, json={"exercise_name": "Snatch", "max_weight_kg": 100})
    plan = coach.post(
        "/plans/",
        json={"name": "Plan con notas", "discipline": "CrossFit", "weeks_count": 1, "training_days": [0]},
    ).json()
    sesion_plan = coach.get(f"/plans/{plan['id']}").json()["sessions"][0]["id"]
    r = coach.post(
        f"/plans/{plan['id']}/sessions/{sesion_plan}/sets",
        json={
            "exercise_name": "Snatch",
            "prescribed_sets": 2,
            "prescribed_reps": 2,
            "prescribed_percentage": 80,
            "coach_note": "Pausa de 2 s en la recepción.",
        },
    )
    assert r.status_code == 200, r.text
    assert coach.put(f"/plans/{plan['id']}/publish", json={"is_published": True, "visibility": "box"}).status_code == 200

    a = atleta_de_coach.post(f"/plans/{plan['id']}/acquire", json={"start_date": str(date.today())})
    assert a.status_code == 200, a.text
    sesiones = atleta_de_coach.get(f"/mesocycles/{a.json()['mesocycle_id']}").json()["sessions"]
    series = [s for ses in sesiones for s in ses["sets"]]
    assert len(series) == 2
    assert all(s["coach_note"] == "Pausa de 2 s en la recepción." for s in series)
    assert all(s["prescribed_weight"] == 80 for s in series)  # 80 % de 100 kg, con SU marca


# ------------------------------------------------------------------ orden de las series

def _orden(coach, meso, sesion):
    sesiones = coach.get(f"/mesocycles/{meso}").json()["sessions"]
    ses = next(s for s in sesiones if s["id"] == sesion)
    return [s["exercise"]["name"] for s in sorted(ses["sets"], key=lambda x: x["set_order"])]


def test_una_serie_nueva_queda_junto_a_las_de_su_ejercicio(coach, atleta_de_coach):
    meso, sesion = _sesion_del_atleta(coach, atleta_de_coach)
    for nombre in ("Snatch", "Snatch", "Press", "Press"):
        assert coach.post(f"/sessions/{sesion}/sets/", json={"exercise_name": nombre, "prescribed_reps": 3}).status_code == 200
    assert coach.post(f"/sessions/{sesion}/sets/", json={"exercise_name": "Snatch", "prescribed_reps": 1}).status_code == 200
    assert _orden(coach, meso, sesion) == ["Snatch", "Snatch", "Snatch", "Press", "Press"]
    # un ejercicio nuevo sigue yendo al final
    coach.post(f"/sessions/{sesion}/sets/", json={"exercise_name": "Row", "prescribed_reps": 8})
    assert _orden(coach, meso, sesion)[-1] == "Row"


def test_borrar_una_serie_no_hace_que_la_siguiente_choque_de_orden(coach, atleta_de_coach):
    meso, sesion = _sesion_del_atleta(coach, atleta_de_coach)
    for nombre in ("A", "A", "B", "B"):
        coach.post(f"/sessions/{sesion}/sets/", json={"exercise_name": nombre, "prescribed_reps": 3})
    a1 = _series(coach, meso, sesion, "A")[0]["id"]
    assert coach.delete(f"/sets/{a1}").status_code == 200          # queda un hueco en el orden
    coach.post(f"/sessions/{sesion}/sets/", json={"exercise_name": "C", "prescribed_reps": 5})
    sesiones = coach.get(f"/mesocycles/{meso}").json()["sessions"]
    ordenes = [s["set_order"] for ses in sesiones if ses["id"] == sesion for s in ses["sets"]]
    assert len(ordenes) == len(set(ordenes)), ordenes                # sin órdenes repetidos
    assert _orden(coach, meso, sesion)[-1] == "C"
