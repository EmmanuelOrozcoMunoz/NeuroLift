"""Lo que se copia al registrar una clase o sumarse a un grupo: nota del coach y cargas por atleta."""
from datetime import date

NOTA = "Sentadilla completa, balón al objetivo."


def _series_de(cuenta, meso_id):
    sesiones = cuenta.get(f"/mesocycles/{meso_id}").json()["sessions"]
    return [s for ses in sesiones for s in ses["sets"]]


def test_registrar_una_clase_copia_la_nota_y_calcula_el_peso_del_atleta(dueno_de_box, atleta_de_box):
    atleta_de_box.post(f"/users/{atleta_de_box.id}/records/", json={"exercise_name": "Snatch", "max_weight_kg": 60})

    clase = dueno_de_box.post(
        "/classes/", json={"name": "Halterofilia", "weekdays": [date.today().weekday()], "start_time": "18:30"}
    )
    assert clase.status_code == 200, clase.text
    dia = dueno_de_box.post(f"/classes/{clase.json()['id']}/days", json={"date": str(date.today())}).json()
    r = dueno_de_box.post(
        f"/sessions/{dia['session_id']}/sets/",
        json={"exercise_name": "Snatch", "prescribed_reps": 2, "prescribed_percentage": 80, "coach_note": NOTA},
    )
    assert r.status_code == 200, r.text

    unido = atleta_de_box.post(f"/classes/sessions/{dia['session_id']}/join")
    assert unido.status_code == 200, unido.text
    assert unido.json()["missing_prs"] == []

    copia = _series_de(atleta_de_box, unido.json()["mesocycle_id"])
    assert len(copia) == 1
    assert copia[0]["coach_note"] == NOTA
    assert copia[0]["prescribed_weight"] == 47.5  # 80 % de SU marca (60 kg), redondeado a 2,5
    # y la clase del profesor sigue igual para el resto
    original = _series_de(dueno_de_box, dia["mesocycle_id"])
    assert original[0]["prescribed_weight"] is None and original[0]["coach_note"] == NOTA


def test_un_miembro_nuevo_del_grupo_recibe_lo_ya_programado_con_su_nota(client, coach, atleta_de_coach, codigo_coach):
    grupo = coach.post("/groups/", json={"name": "Competidores", "athlete_ids": [atleta_de_coach.id]}).json()
    programa = {
        "group_id": grupo["id"],
        "name": "Bloque grupal",
        "discipline": "CrossFit",
        "start_date": str(date.today()),
        "weeks_count": 1,
        "training_days": [date.today().weekday()],
    }
    assert coach.post("/mesocycles/manual/group", json=programa).status_code == 200
    base = {"program_name": "Bloque grupal", "program_start_date": str(date.today()), "scheduled_date": str(date.today())}
    r = coach.post(
        f"/groups/{grupo['id']}/sessions/bulk-add-exercise",
        json={**base, "exercise_name": "Muscle-up", "prescribed_sets": 2, "prescribed_reps": 3, "coach_note": "Kipping controlado."},
    )
    assert r.status_code == 200, r.text

    nuevo = client.post(
        "/auth/register",
        json={"email": f"nuevo-{grupo['id'][:8]}@example.com", "full_name": "Nuevo", "password": "password123", "invite_code": codigo_coach},
    )
    assert nuevo.status_code == 200, nuevo.text
    nuevo_id = client.post("/auth/login", json={"email": f"nuevo-{grupo['id'][:8]}@example.com", "password": "password123"})
    assert nuevo_id.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {nuevo_id.json()['access_token']}"}).json()

    assert coach.post(f"/groups/{grupo['id']}/members", json={"athlete_ids": [me["id"]]}).status_code == 200

    mesos = coach.get(f"/users/{me['id']}/mesocycles/").json()
    assert len(mesos) == 1
    series = _series_de(coach, mesos[0]["id"])
    assert len(series) == 2
    assert all(s["coach_note"] == "Kipping controlado." and s["exercise"]["name"] == "Muscle-up" for s in series)
