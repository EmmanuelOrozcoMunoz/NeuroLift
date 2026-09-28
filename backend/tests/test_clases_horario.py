"""Horario de clases y registro del atleta: lo que pasa por services/classes.py."""
from datetime import date, timedelta

from backend.tests.conftest import crear_atleta_de_box, crear_box_activo

HOY = date.today()


def _clase_con_contenido(dueno, dia=HOY, nombre="Open WOD"):
    """Crea una clase que se dicta `dia`, con ese día programado y un ejercicio."""
    clase = dueno.post("/classes/", json={"name": nombre, "weekdays": [dia.weekday()], "start_time": "06:00"})
    assert clase.status_code == 200, clase.text
    programado = dueno.post(f"/classes/{clase.json()['id']}/days", json={"date": str(dia)}).json()
    dueno.post(f"/sessions/{programado['session_id']}/sets/", json={"exercise_name": "Thruster", "prescribed_reps": 10})
    return clase.json(), programado


def _de_hoy(cuenta, nombre):
    r = cuenta.get("/classes/schedule", params={"start": str(HOY), "days": 1})
    assert r.status_code == 200, r.text
    return next(o for o in r.json() if o["class_name"] == nombre)


def test_el_horario_muestra_hora_contenido_y_si_el_atleta_ya_la_registro(dueno_de_box, atleta_de_box):
    _, dia = _clase_con_contenido(dueno_de_box)

    antes = _de_hoy(atleta_de_box, "Open WOD")
    assert antes["start_time"] == "06:00"
    assert [s["exercise"]["name"] for s in antes["session"]["sets"]] == ["Thruster"]
    assert antes["my_session_id"] is None

    registro = atleta_de_box.post(f"/classes/sessions/{dia['session_id']}/join").json()
    despues = _de_hoy(atleta_de_box, "Open WOD")
    assert despues["my_session_id"] == registro["session_id"]
    assert despues["my_mesocycle_id"] == registro["mesocycle_id"]
    assert _de_hoy(dueno_de_box, "Open WOD")["my_session_id"] is None  # solo lo ve quien la registró


def test_registrar_dos_veces_devuelve_la_misma_copia_y_se_puede_quitar(dueno_de_box, atleta_de_box):
    _, dia = _clase_con_contenido(dueno_de_box)
    ruta = f"/classes/sessions/{dia['session_id']}/join"

    primera = atleta_de_box.post(ruta).json()
    segunda = atleta_de_box.post(ruta).json()
    assert primera["session_id"] == segunda["session_id"]

    assert atleta_de_box.delete(ruta).status_code == 200
    assert _de_hoy(atleta_de_box, "Open WOD")["my_session_id"] is None
    assert atleta_de_box.delete(ruta).status_code == 404
    assert atleta_de_box.post(ruta).json()["session_id"] != primera["session_id"]  # copia nueva y limpia


def test_no_se_registra_una_clase_futura(dueno_de_box, atleta_de_box):
    _, manana = _clase_con_contenido(dueno_de_box, dia=HOY + timedelta(days=1), nombre="Mañana")
    assert atleta_de_box.post(f"/classes/sessions/{manana['session_id']}/join").status_code == 400


def test_una_clase_de_otro_box_responde_como_si_no_existiera(client, dueno_de_box):
    _, dia = _clase_con_contenido(dueno_de_box)
    otro_dueno = crear_box_activo(client)
    atleta_ajeno = crear_atleta_de_box(client, otro_dueno)
    assert atleta_ajeno.post(f"/classes/sessions/{dia['session_id']}/join").status_code == 404
    assert [o for o in atleta_ajeno.get("/classes/schedule", params={"start": str(HOY), "days": 1}).json()] == []


def test_un_atleta_solo_no_ve_horario_ni_registra_clases(dueno_de_box, atleta_solo):
    _, dia = _clase_con_contenido(dueno_de_box)
    assert atleta_solo.get("/classes/schedule", params={"start": str(HOY), "days": 1}).status_code == 403
    assert atleta_solo.post(f"/classes/sessions/{dia['session_id']}/join").status_code == 403
