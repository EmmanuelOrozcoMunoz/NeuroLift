"""Ranking del box entre atletas: marcas (1RM) y WODs."""
import uuid
from datetime import date, timedelta
from urllib.parse import quote

import pytest

from backend.tests.conftest import PASSWORD, Cuenta, _login, crear_atleta_de_box, crear_box_activo

HOY = date.today()


def _atleta(client, codigo, nombre) -> Cuenta:
    email = f"{nombre.lower()}-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "full_name": nombre, "password": PASSWORD, "invite_code": codigo})
    assert r.status_code == 200, r.text
    return _login(client, email)


@pytest.fixture
def equipo(client, coach, codigo_coach):
    """Una cuenta (coach independiente) con tres atletas."""
    return coach, [_atleta(client, codigo_coach, n) for n in ("Ana", "Beto", "Carla")]


def _marca(cuenta, ejercicio, kg):
    r = cuenta.post(f"/users/{cuenta.id}/records/", json={"exercise_name": ejercicio, "max_weight_kg": kg})
    assert r.status_code == 200, r.text


def _tabla_marcas(cuenta, clave, **params):
    r = cuenta.get(f"/ranking/lifts/{quote(clave)}", params=params)
    assert r.status_code == 200, r.text
    return [(f["full_name"], f["rank"], f["weight_kg"]) for f in r.json()]


# ------------------------------------------------------------------ marcas

def test_el_ranking_de_marcas_ordena_de_mayor_a_menor_y_unifica_los_nombres(equipo):
    _, (ana, beto, carla) = equipo
    _marca(ana, "Back Squat", 100)
    _marca(beto, "back squat", 120)          # otro nombre, mismo levantamiento
    _marca(carla, "Clean & Jerk", 60)
    _marca(ana, "Clean and jerk", 70)

    lista = {l["name"]: l["athletes_count"] for l in ana.get("/ranking/lifts").json()}
    assert lista == {"back squat": 2, "Clean and jerk": 2} or set(lista.values()) == {2}
    assert len(lista) == 2                       # dos levantamientos, no cuatro

    assert _tabla_marcas(ana, "Back Squat") == [("Beto", 1, 120), ("Ana", 2, 100)]
    assert _tabla_marcas(ana, "clean & jerk") == [("Ana", 1, 70), ("Carla", 2, 60)]
    yo = [f for f in ana.get(f"/ranking/lifts/{quote('back squat')}").json() if f["is_me"]]
    assert [f["full_name"] for f in yo] == ["Ana"]


def test_cada_atleta_cuenta_con_su_mejor_marca_y_los_empates_comparten_posicion(equipo):
    _, (ana, beto, carla) = equipo
    _marca(ana, "Snatch", 60)
    _marca(ana, "snatch", 80)                # su mejor marca cuenta
    _marca(beto, "Snatch", 80)
    _marca(carla, "Snatch", 50)
    assert _tabla_marcas(carla, "Snatch") == [("Ana", 1, 80), ("Beto", 1, 80), ("Carla", 3, 50)]


def test_quien_apaga_su_aparicion_desaparece_y_se_puede_volver_a_encender(equipo):
    _, (ana, beto, _carla) = equipo
    _marca(ana, "Deadlift", 150)
    _marca(beto, "Deadlift", 140)
    assert ana.put("/users/me/preferences", json={"show_in_ranking": False}).json()["show_in_ranking"] is False
    assert _tabla_marcas(beto, "Deadlift") == [("Beto", 1, 140)]
    assert ana.put("/users/me/preferences", json={"show_in_ranking": True}).status_code == 200
    assert [n for n, _, _ in _tabla_marcas(beto, "Deadlift")] == ["Ana", "Beto"]


def test_el_ranking_se_puede_filtrar_por_sexo(equipo):
    _, (ana, beto, carla) = equipo
    for cuenta, sexo in ((ana, "female"), (beto, "male"), (carla, "female")):
        assert cuenta.put(f"/users/{cuenta.id}/fitness-benchmarks", json={"sex": sexo}).status_code == 200
        _marca(cuenta, "Back Squat", {"Ana": 90, "Beto": 140, "Carla": 80}[cuenta.datos["full_name"]])
    assert _tabla_marcas(ana, "Back Squat", sex="female") == [("Ana", 1, 90), ("Carla", 2, 80)]
    assert _tabla_marcas(ana, "Back Squat", sex="male") == [("Beto", 1, 140)]
    assert [n for n, _, _ in _tabla_marcas(ana, "Back Squat")] == ["Beto", "Ana", "Carla"]


def test_solo_ven_el_ranking_los_de_esa_cuenta_y_no_se_mezclan_los_boxes(client, equipo, dueno_de_box):
    _, (ana, _beto, _carla) = equipo
    _marca(ana, "Back Squat", 100)
    ajeno = crear_atleta_de_box(client, dueno_de_box)
    _marca(ajeno, "Back Squat", 300)
    assert _tabla_marcas(ana, "Back Squat") == [("Ana", 1, 100)]
    assert _tabla_marcas(ajeno, "Back Squat") == [(ajeno.datos["full_name"], 1, 300)]


def test_el_ranking_no_existe_para_un_atleta_solo_pero_el_coach_lo_ve(equipo, atleta_solo):
    coach, (ana, *_) = equipo
    _marca(ana, "Back Squat", 100)
    r = atleta_solo.get("/ranking/lifts")
    assert r.status_code == 403 and r.json()["detail"] == "El ranking es de tu box"
    assert _tabla_marcas(coach, "Back Squat") == [("Ana", 1, 100)]     # el entrenador también lo ve


# ------------------------------------------------------------------ WODs

def _wod(cuenta, nombre, formato, dias_atras=0, completar=True, **resultado):
    """El atleta anota a mano un WOD: sesión propia + ejercicio metabólico + formato + resultado."""
    fecha = str(HOY - timedelta(days=dias_atras))
    sesion = cuenta.post("/users/me/personal-sessions", json={"scheduled_date": fecha}).json()
    r = cuenta.post(f"/sessions/{sesion['id']}/sets/", json={"exercise_name": nombre, "prescribed_reps": 1, "block": "metcon"})
    assert r.status_code == 200, r.text
    r = cuenta.put(f"/sessions/{sesion['id']}/wod-format", json={"wod_format": formato})
    assert r.status_code == 200, r.text
    if completar:
        r = cuenta.post(f"/sessions/{sesion['id']}/complete", json=resultado)
        assert r.status_code == 200, r.text
    return sesion


def _tabla_wod(cuenta, clave, formato, **params):
    r = cuenta.get(f"/ranking/wods/{quote(clave)}", params={"wod_format": formato, **params})
    assert r.status_code == 200, r.text
    return [(f["full_name"], f["rank"], f["score_label"]) for f in r.json()]


def test_ranking_de_un_wod_por_tiempo_gana_el_menor_y_cuenta_el_mejor_intento(equipo):
    _, (ana, beto, carla) = equipo
    _wod(ana, "Fran", "for_time", 3, wod_time_seconds=300)
    _wod(ana, "fran", "for_time", 1, wod_time_seconds=230)       # mejor intento de Ana
    _wod(beto, "Fran", "for_time", 2, wod_time_seconds=250)
    _wod(carla, "Fran", "for_time", 0, completar=False)           # sin completar: no cuenta

    lista = ana.get("/ranking/wods").json()
    assert [(w["name"], w["wod_format"], w["athletes_count"]) for w in lista] == [("Fran", "for_time", 2)]
    assert _tabla_wod(ana, "Fran", "for_time") == [("Ana", 1, "Por tiempo: 3:50"), ("Beto", 2, "Por tiempo: 4:10")]


def test_en_un_amrap_gana_el_mayor_y_cada_formato_es_un_ranking_aparte(equipo):
    _, (ana, beto, _carla) = equipo
    _wod(ana, "Cindy", "amrap", 1, wod_rounds=18, wod_extra_reps=3)
    _wod(beto, "Cindy", "amrap", 2, wod_rounds=20, wod_extra_reps=0)
    _wod(beto, "Cindy", "for_time", 3, wod_time_seconds=1500)     # mismo nombre, otro formato
    assert [(w["name"], w["wod_format"]) for w in ana.get("/ranking/wods").json()] == [("Cindy", "amrap"), ("Cindy", "for_time")]
    assert [n for n, _, _ in _tabla_wod(ana, "Cindy", "amrap")] == ["Beto", "Ana"]
    assert [n for n, _, _ in _tabla_wod(ana, "Cindy", "for_time")] == ["Beto"]


def test_los_wods_que_programa_el_coach_no_aparecen_en_el_ranking(equipo):
    coach, (ana, beto, _carla) = equipo
    creado = coach.post("/mesocycles/manual", json={
        "user_id": ana.id, "name": "Bloque", "discipline": "CrossFit",
        "start_date": str(HOY), "weeks_count": 1, "training_days": [0, 1, 2, 3, 4, 5, 6],
    }).json()
    sesion = coach.get(f"/mesocycles/{creado['mesocycle_id']}").json()["sessions"][0]["id"]
    coach.post(f"/sessions/{sesion}/sets/", json={"exercise_name": "WOD secreto del coach", "prescribed_reps": 1, "block": "metcon"})
    coach.put(f"/sessions/{sesion}/wod-format", json={"wod_format": "for_time"})
    assert ana.post(f"/sessions/{sesion}/complete", json={"wod_time_seconds": 600}).status_code == 200
    _wod(beto, "Fran", "for_time", 0, wod_time_seconds=240)
    assert [w["name"] for w in beto.get("/ranking/wods").json()] == ["Fran"]     # el del coach no sale


def test_un_registro_antiguo_de_clase_no_filtra_el_nombre_de_su_wod(equipo):
    from backend import models
    from backend.database import SessionLocal

    _, (ana, beto, _carla) = equipo
    with SessionLocal() as db:
        meso = models.Mesocycle(user_id=uuid.UUID(ana.id), box_id=uuid.UUID(ana.datos["box"]["id"]), name="Clases del box",
                                discipline="Clase", start_date=HOY, is_class_log=True, is_self_managed=True)
        db.add(meso)
        db.flush()
        sesion = models.Session(mesocycle_id=meso.id, scheduled_date=HOY, status="completed",
                                wod_format="for_time", wod_time_seconds=500)
        db.add(sesion)
        db.flush()
        ejercicio = models.Exercise(name=f"WOD de la clase {uuid.uuid4().hex[:6]}", category="Custom")
        db.add(ejercicio)
        db.flush()
        db.add(models.Set(session_id=sesion.id, exercise_id=ejercicio.id, set_order=1, prescribed_reps=1, block="metcon"))
        db.commit()
    assert beto.get("/ranking/wods").json() == []


def test_quien_apaga_su_aparicion_tampoco_sale_en_los_wods(equipo):
    _, (ana, beto, _carla) = equipo
    _wod(ana, "Grace", "for_time", 0, wod_time_seconds=200)
    _wod(beto, "Grace", "for_time", 1, wod_time_seconds=220)
    ana.put("/users/me/preferences", json={"show_in_ranking": False})
    assert _tabla_wod(beto, "Grace", "for_time") == [("Beto", 1, "Por tiempo: 3:40")]
