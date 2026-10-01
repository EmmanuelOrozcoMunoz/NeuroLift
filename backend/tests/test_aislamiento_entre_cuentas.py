"""Un coach que, por un dato inconsistente, tiene "como suyo" a un atleta de OTRA cuenta no puede
ver ni tocar nada de ese atleta. La frontera entre cuentas (boxes) manda sobre `coach_id`."""
from datetime import date

import pytest

from backend.tests.conftest import crear_atleta_de_box


@pytest.fixture
def atleta_ajeno_con_mi_coach_id(coach, client, dueno_de_box):
    """Atleta de OTRO box cuyo coach_id apunta a `coach` (lo que pasaría con un dato mal cargado)."""
    from backend import models
    from backend.database import SessionLocal

    ajeno = crear_atleta_de_box(client, dueno_de_box)
    with SessionLocal() as db:
        db.query(models.User).filter(models.User.id == ajeno.id).update({"coach_id": coach.id})
        db.commit()
    return ajeno


def test_el_coach_no_ve_ni_toca_al_atleta_de_otra_cuenta(coach, dueno_de_box, atleta_ajeno_con_mi_coach_id):
    a = atleta_ajeno_con_mi_coach_id

    # no aparece en su lista de atletas
    lista = coach.get("/users/athletes").json()
    assert a.id not in {x["id"] for x in lista}

    # no puede ver sus datos ni programarle nada
    assert coach.get(f"/users/{a.id}/mesocycles/").status_code == 403
    assert coach.get(f"/users/{a.id}/records/").status_code == 403
    crear = coach.post("/mesocycles/manual", json={
        "user_id": a.id, "name": "Intruso", "discipline": "CrossFit",
        "start_date": str(date.today()), "weeks_count": 1, "training_days": [0],
    })
    assert crear.status_code == 403

    # tampoco lo puede meter en un grupo suyo
    assert coach.post("/groups/", json={"name": "Robo", "athlete_ids": [a.id]}).status_code == 403

    # el dueño de SU box sí lo ve (la frontera es la cuenta)
    assert dueno_de_box.get(f"/users/{a.id}/mesocycles/").status_code == 200


def test_un_atleta_de_un_box_no_puede_cambiarse_a_otra_cuenta_por_su_cuenta(client, dueno_de_box, atleta_de_box, coach, codigo_coach):
    r = atleta_de_box.post("/boxes/join", json={"invite_code": codigo_coach})
    assert r.status_code == 400
    assert atleta_de_box.get("/auth/me").json()["box"]["id"] == dueno_de_box.datos["box"]["id"]


def test_el_coach_solo_puede_asignar_atletas_de_su_propio_box(dueno_de_box, atleta_de_box, client):
    from backend.tests.conftest import crear_box_activo

    otro_dueno = crear_box_activo(client)
    r = otro_dueno.put(f"/boxes/me/athletes/{atleta_de_box.id}/coach", json={"coach_id": otro_dueno.id})
    assert r.status_code == 404          # para el otro dueño, ese atleta "no existe" en su box
