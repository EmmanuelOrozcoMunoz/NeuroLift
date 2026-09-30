"""Códigos y mensajes de error que ve el frontend, fijados uno por uno.

Sirven de red de seguridad para cambiar CÓMO se lanzan los errores (excepciones de dominio con
un manejador único) sin cambiar lo que el cliente recibe: mismo código, mismo `detail` y, en los
401, la cabecera WWW-Authenticate.
"""
import uuid

import pytest

from backend.tests.conftest import (
    PASSWORD,
    _admin,
    _email,
    _login,
    crear_atleta_de_box,
    crear_box_activo,
)


def error(resp, codigo, detalle):
    assert resp.status_code == codigo, resp.text
    assert resp.json()["detail"] == detalle


# ------------------------------------------------------------------ autenticación

def test_sin_token(client):
    error(client.get("/auth/me"), 401, "Not authenticated")


def test_token_invalido_lleva_la_cabecera_www_authenticate(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer esto.no.es.un.jwt"})
    error(r, 401, "No se pudieron validar las credenciales")
    assert r.headers["www-authenticate"] == "Bearer"


def test_token_revocado_tras_cerrar_sesion(client, atleta_solo):
    assert atleta_solo.post("/auth/logout").status_code == 200
    r = atleta_solo.get("/auth/me")
    error(r, 401, "Esta sesión fue cerrada. Inicia sesión de nuevo.")
    assert r.headers["www-authenticate"] == "Bearer"


def test_miembro_de_un_box_suspendido(client, dueno_de_box, atleta_de_box):
    box_id = dueno_de_box.datos["box"]["id"]
    assert _admin(client).put(f"/admin/boxes/{box_id}/status", json={"status": "suspended"}).status_code == 200
    error(atleta_de_box.get("/auth/me"), 403, "Tu box no está activo en este momento. Contacta a su administrador.")


# ------------------------------------------------------------------ roles

def test_un_atleta_no_es_coach(atleta_solo):
    error(atleta_solo.post("/groups/", json={"name": "x"}), 403, "Acción reservada para coaches")


def test_un_dueno_con_el_box_pendiente_no_programa(client):
    email = _email("pendiente")
    client.post("/boxes/register", json={
        "box_name": "Box Pendiente", "city": "Cali", "owner_name": "Dueña", "email": email, "password": PASSWORD,
    })
    error(_login(client, email).post("/groups/", json={"name": "x"}),
          403, "Tu box todavía no está activo: podrás programar en cuanto lo aprueben.")


def test_un_coach_de_box_no_es_dueno_ni_admin(client, dueno_de_box):
    email = _email("profe")
    assert dueno_de_box.post("/boxes/me/coaches", json={"full_name": "Profe", "email": email, "password": PASSWORD}).status_code == 200
    profe = _login(client, email)
    error(profe.post("/classes/", json={"name": "x", "weekdays": [0], "start_time": "07:00"}),
          403, "Acción reservada al dueño del box")
    error(profe.get("/admin/boxes"), 403, "Acción reservada para administradores")


# ------------------------------------------------------------------ pertenencia

def test_un_coach_no_ve_a_los_atletas_de_otro(client, atleta_de_coach):
    otro = _login(client, _registrar_coach(client))
    error(otro.get(f"/users/{atleta_de_coach.id}/mesocycles/"), 403, "No tienes permiso sobre este recurso")


def _registrar_coach(client):
    email = _email("coach")
    assert client.post("/boxes/register-coach", json={"full_name": "Otro Coach", "email": email, "password": PASSWORD}).status_code == 200
    return email


def test_solo_el_profesor_o_el_dueno_programan_una_clase(client, dueno_de_box):
    clase = dueno_de_box.post("/classes/", json={"name": "Open", "weekdays": [0], "start_time": "07:00"}).json()
    email = _email("profe")
    creado = dueno_de_box.post("/boxes/me/coaches", json={"full_name": "Profe", "email": email, "password": PASSWORD})
    assert creado.status_code == 200, creado.text
    profe = _login(client, email)
    error(profe.post(f"/classes/{clase['id']}/days", json={"date": "2026-01-05"}),
          403, "Solo el profesor de esta clase o el dueño del box pueden programarla")


def test_la_programacion_de_una_clase_es_solo_del_box(client, dueno_de_box):
    clase = dueno_de_box.post("/classes/", json={"name": "Open", "weekdays": [0], "start_time": "07:00"}).json()
    dia = dueno_de_box.post(f"/classes/{clase['id']}/days", json={"date": "2026-01-05"}).json()
    ajeno = crear_atleta_de_box(client, crear_box_activo(client))
    error(ajeno.get(f"/mesocycles/{dia['mesocycle_id']}"), 403, "Esta clase es de otro box")


def test_mesociclo_para_un_atleta_sin_coach_personal(dueno_de_box, atleta_de_box):
    r = dueno_de_box.post("/mesocycles/manual", json={
        "user_id": atleta_de_box.id, "name": "x", "discipline": "CrossFit",
        "start_date": "2026-01-05", "weeks_count": 1, "training_days": [0],
    })
    error(r, 400, "Los mesociclos son para atletas con coach personal. Sin coach: "
                  f"{atleta_de_box.datos['full_name']}. Asígnales uno en Equipo.")


def test_el_atleta_no_edita_lo_que_prescribio_su_coach(coach, atleta_de_coach):
    from datetime import date
    m = coach.post("/mesocycles/manual", json={
        "user_id": atleta_de_coach.id, "name": "B", "discipline": "CrossFit",
        "start_date": str(date.today()), "weeks_count": 1, "training_days": [0, 1, 2, 3, 4, 5, 6],
    }).json()
    sesion = coach.get(f"/mesocycles/{m['mesocycle_id']}").json()["sessions"][0]["id"]
    coach.post(f"/sessions/{sesion}/sets/", json={"exercise_name": "Press", "prescribed_reps": 5})
    serie = coach.get(f"/mesocycles/{m['mesocycle_id']}").json()["sessions"][0]["sets"][0]["id"]
    error(atleta_de_coach.put(f"/sets/{serie}", json={"exercise_name": "Press", "prescribed_reps": 5}),
          403, "Esta sesión la prescribió tu coach — solo tu coach puede editarla")


# ------------------------------------------------------------------ grupos

def test_grupo_inexistente_y_grupo_ajeno(client, coach):
    error(coach.get(f"/groups/{uuid.uuid4()}"), 404, "Grupo no encontrado")
    grupo = coach.post("/groups/", json={"name": "Mío"}).json()
    otro = _login(client, _registrar_coach(client))
    error(otro.get(f"/groups/{grupo['id']}"), 403, "Este grupo no te pertenece")


def test_agregar_atletas_de_otro_box_o_de_otro_coach(client, coach, atleta_de_coach):
    grupo = coach.post("/groups/", json={"name": "Mío"}).json()
    de_otro_box = crear_atleta_de_box(client, crear_box_activo(client))
    error(coach.post(f"/groups/{grupo['id']}/members", json={"athlete_ids": [de_otro_box.id]}),
          403, "Uno o más atletas no pertenecen a tu box")

    otro_coach = _login(client, _registrar_coach(client))
    error(otro_coach.post("/groups/", json={"name": "Del otro", "athlete_ids": [atleta_de_coach.id]}),
          403, "Uno o más atletas no pertenecen a tu box")


def test_el_dueno_no_agrega_a_un_grupo_atletas_sin_coach(dueno_de_box, atleta_de_box):
    r = dueno_de_box.post("/groups/", json={"name": "General", "athlete_ids": [atleta_de_box.id]})
    error(r, 400, "Estos atletas no tienen coach personal: "
                  f"{atleta_de_box.datos['full_name']}. Asígnales uno en Equipo.")


def test_portada_de_grupo_inexistente(coach):
    grupo = coach.post("/groups/", json={"name": "Sin portada"}).json()
    error(coach.get(f"/groups/{grupo['id']}/cover"), 404, "No hay imagen.")


# ------------------------------------------------------------------ suscripción

def test_suscripcion_vencida_y_limite_de_atletas(client, coach, codigo_coach, monkeypatch):
    from datetime import datetime, timedelta

    from backend import models
    from backend.core import billing
    from backend.database import SessionLocal

    def registrar(nombre):
        return client.post("/auth/register", json={
            "email": _email(nombre), "full_name": nombre, "password": PASSWORD, "invite_code": codigo_coach,
        })

    monkeypatch.setitem(billing.PLANS["basic"], "max_athletes", 1)
    assert registrar("uno").status_code == 200
    error(registrar("dos"), 403, "Se alcanzó el límite de 1 atletas del plan actual. Hay que subir de plan para agregar más.")

    with SessionLocal() as db:
        box = db.query(models.Box).filter(models.Box.id == coach.datos["box"]["id"]).one()
        box.trial_ends_at = datetime.utcnow() - timedelta(days=1)
        box.paid_until = None
        db.commit()
    error(registrar("tres"), 403, "La suscripción de tu coach venció: no se pueden agregar atletas nuevos por ahora.")


# ------------------------------------------------------------------ imágenes

def test_avatar_vacio_se_rechaza(atleta_solo):
    r = atleta_solo.post("/users/me/avatar", files={"file": ("a.png", b"", "image/png")})
    error(r, 400, "El archivo está vacío.")


# ------------------------------------------------------------------ auditoría

def _entradas_de_auditoria(fragmento):
    from backend import models
    from backend.database import SessionLocal

    with SessionLocal() as db:
        return db.query(models.AuditLog).filter(models.AuditLog.message.contains(fragmento)).count()


def test_los_401_y_403_de_dominio_quedan_en_la_auditoria_pero_los_404_no(client, atleta_solo):
    antes_403 = _entradas_de_auditoria("Acción reservada para coaches")
    antes_401 = _entradas_de_auditoria("No se pudieron validar las credenciales")
    antes_404 = _entradas_de_auditoria("Grupo no encontrado")

    atleta_solo.post("/groups/", json={"name": "x"})
    client.get("/auth/me", headers={"Authorization": "Bearer basura"})
    coach = _login(client, _registrar_coach(client))
    coach.get(f"/groups/{uuid.uuid4()}")

    assert _entradas_de_auditoria("Acción reservada para coaches") == antes_403 + 1
    assert _entradas_de_auditoria("No se pudieron validar las credenciales") == antes_401 + 1
    assert _entradas_de_auditoria("Grupo no encontrado") == antes_404


def test_un_atleta_del_mismo_box_no_ve_la_programacion_de_una_clase(dueno_de_box, atleta_de_box):
    clase = dueno_de_box.post("/classes/", json={"name": "Open", "weekdays": [0], "start_time": "07:00"}).json()
    dia = dueno_de_box.post(f"/classes/{clase['id']}/days", json={"date": "2026-01-05"}).json()
    error(atleta_de_box.get(f"/mesocycles/{dia['mesocycle_id']}"), 403,
          "La programación de las clases es solo para los entrenadores del box")
