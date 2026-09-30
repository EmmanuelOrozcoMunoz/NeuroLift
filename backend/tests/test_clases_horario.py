"""Clases del box: módulo solo para los entrenadores del box. Los atletas no ven horario ni contenido."""
from datetime import date

from backend.tests.conftest import PASSWORD, _email, _login, crear_box_activo

HOY = date.today()


def _coach_del_box(client, dueno, nombre="Profe"):
    email = _email(nombre.lower())
    creado = dueno.post("/boxes/me/coaches", json={"full_name": nombre, "email": email, "password": PASSWORD})
    assert creado.status_code == 200, creado.text
    return _login(client, email)


def _clase_con_contenido(dueno, profesor=None, dia=HOY, nombre="Open WOD"):
    """Crea una clase que se dicta `dia` (con ese profesor), programada, con un ejercicio."""
    cuerpo = {"name": nombre, "weekdays": [dia.weekday()], "start_time": "06:00"}
    if profesor is not None:
        cuerpo["coach_id"] = profesor.id
    clase = dueno.post("/classes/", json=cuerpo)
    assert clase.status_code == 200, clase.text
    programado = dueno.post(f"/classes/{clase.json()['id']}/days", json={"date": str(dia)}).json()
    dueno.post(f"/sessions/{programado['session_id']}/sets/", json={"exercise_name": "Thruster", "prescribed_reps": 10})
    return clase.json(), programado


def _de_hoy(cuenta, nombre):
    r = cuenta.get("/classes/schedule", params={"start": str(HOY), "days": 1})
    assert r.status_code == 200, r.text
    return next(o for o in r.json() if o["class_name"] == nombre)


def test_el_dueno_y_los_coaches_del_box_ven_el_horario_con_su_contenido(client, dueno_de_box):
    profe = _coach_del_box(client, dueno_de_box)
    _clase_con_contenido(dueno_de_box, profesor=profe)

    for quien in (dueno_de_box, profe, _coach_del_box(client, dueno_de_box, "Otro")):
        clase = _de_hoy(quien, "Open WOD")
        assert clase["start_time"] == "06:00"
        assert clase["coach_name"] == "Profe"
        assert [s["exercise"]["name"] for s in clase["session"]["sets"]] == ["Thruster"]
        assert "my_session_id" not in clase   # ya no existe el registro de atletas


def test_solo_el_profesor_y_el_dueno_pueden_programar_los_demas_coaches_solo_ven(client, dueno_de_box):
    profe = _coach_del_box(client, dueno_de_box)
    otro = _coach_del_box(client, dueno_de_box, "Otro")
    _clase_con_contenido(dueno_de_box, profesor=profe)

    assert _de_hoy(dueno_de_box, "Open WOD")["can_program"] is True
    assert _de_hoy(profe, "Open WOD")["can_program"] is True
    assert _de_hoy(otro, "Open WOD")["can_program"] is False


def test_un_atleta_del_box_no_ve_ni_el_horario_ni_el_contenido(dueno_de_box, atleta_de_box):
    clase, dia = _clase_con_contenido(dueno_de_box)

    for ruta in ("/classes/", "/classes/schedule?start=%s&days=1" % HOY):
        r = atleta_de_box.get(ruta)
        assert r.status_code == 403, ruta
        assert r.json()["detail"] == "Las clases son solo para los entrenadores del box"

    # tampoco puede pedir directamente la programación de la clase ni su lista de programas
    assert atleta_de_box.get(f"/mesocycles/{dia['mesocycle_id']}").status_code == 403
    assert atleta_de_box.get(f"/classes/{clase['id']}/programs").status_code == 403


def test_un_atleta_ya_no_puede_registrar_una_clase(dueno_de_box, atleta_de_box):
    _, dia = _clase_con_contenido(dueno_de_box)
    # el endpoint de registro se eliminó: solo queda DELETE en esa ruta
    assert atleta_de_box.post(f"/classes/sessions/{dia['session_id']}/join").status_code in (404, 405)
    assert atleta_de_box.get(f"/classes/sessions/{dia['session_id']}/join").status_code in (404, 405)


def test_los_coaches_de_otro_box_no_ven_estas_clases(client, dueno_de_box):
    clase, dia = _clase_con_contenido(dueno_de_box)
    otro_dueno = crear_box_activo(client)
    ajeno = _coach_del_box(client, otro_dueno, "Ajeno")

    assert ajeno.get("/classes/schedule", params={"start": str(HOY), "days": 1}).json() == []
    assert otro_dueno.get("/classes/schedule", params={"start": str(HOY), "days": 1}).json() == []
    assert ajeno.get(f"/mesocycles/{dia['mesocycle_id']}").status_code == 403
    assert otro_dueno.get(f"/classes/{clase['id']}/programs").status_code == 404


def test_un_atleta_solo_ni_un_coach_independiente_tienen_clases(coach, atleta_solo):
    assert atleta_solo.get("/classes/schedule", params={"start": str(HOY), "days": 1}).status_code == 403
    assert coach.get("/classes/schedule", params={"start": str(HOY), "days": 1}).status_code == 403


def test_un_atleta_puede_quitar_un_registro_antiguo_pero_no_tiene_ninguno_nuevo(dueno_de_box, atleta_de_box):
    _, dia = _clase_con_contenido(dueno_de_box)
    r = atleta_de_box.delete(f"/classes/sessions/{dia['session_id']}/join")
    assert r.status_code == 404 and r.json()["detail"] == "No tenías registrada esta clase"


# ------------------------------------------------------------------ purga de registros antiguos

def test_el_script_de_purga_cuenta_sin_borrar_y_solo_borra_registros_de_clase(atleta_de_box):
    from datetime import date as _date

    from backend import models
    from backend.database import SessionLocal
    from backend.scripts.purgar_registros_de_clase import purgar_registros_de_clase

    with SessionLocal() as db:
        propia = models.Mesocycle(user_id=atleta_de_box.id, box_id=atleta_de_box.datos["box"]["id"], name="Propia",
                                  discipline="General", start_date=_date.today(), is_self_managed=True)
        registro = models.Mesocycle(user_id=atleta_de_box.id, box_id=atleta_de_box.datos["box"]["id"], name="Clases del box",
                                    discipline="Clase", start_date=_date.today(), is_class_log=True)
        db.add_all([propia, registro])
        db.flush()
        sesion = models.Session(mesocycle_id=registro.id, scheduled_date=_date.today())
        db.add(sesion)
        db.flush()
        db.add(models.Set(session_id=sesion.id, set_order=1, prescribed_reps=5))
        db.commit()
        ids = (propia.id, registro.id)

        antes = purgar_registros_de_clase(db, ejecutar=False)
        assert antes["mesociclos"] >= 1 and antes["series"] >= 1
        assert db.get(models.Mesocycle, ids[1]) is not None            # contar no borra

        purgar_registros_de_clase(db, ejecutar=True)
        db.expire_all()
        assert db.get(models.Mesocycle, ids[1]) is None                  # el registro de clase se fue
        assert db.get(models.Mesocycle, ids[0]) is not None              # su sesión propia sigue
        assert purgar_registros_de_clase(db)["mesociclos"] == 0


def test_el_mensaje_del_script_de_purga_se_puede_imprimir_en_la_consola_de_windows():
    from backend.scripts.purgar_registros_de_clase import mensaje

    resumen = {"atletas": 2, "mesociclos": 3, "sesiones": 4, "series": 5}
    for borrado in (False, True):
        mensaje(resumen, borrado).encode("cp1252")        # no debe lanzar UnicodeEncodeError
    assert "BORRADOS" in mensaje(resumen, True) and "no se borró nada" in mensaje(resumen, False)
