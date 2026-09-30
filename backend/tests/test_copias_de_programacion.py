"""Lo que se copia al sumarse a un grupo: nota del coach y cargas por atleta."""
from datetime import date

def _series_de(cuenta, meso_id):
    sesiones = cuenta.get(f"/mesocycles/{meso_id}").json()["sessions"]
    return [s for ses in sesiones for s in ses["sets"]]


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
