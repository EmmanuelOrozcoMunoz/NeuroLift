"""Bloques con nombre propio ("Activación", "Finisher"...): el coach o el atleta los crean y salen con ese nombre."""
import pytest

from backend.services.block_notes import es_bloque_personalizado
from backend.tests.test_asignar_plan import _asignar_a_atleta, _mesociclo, grupo, plantilla, _asignar  # noqa: F401  (fixtures)
from backend.tests.test_entrenos_del_coach import LUNES, _dia_de_atleta, _dia_de_grupo, _entrenos, _sesiones


@pytest.mark.parametrize("clave, valida", [
    ("x:Activación", True),
    ("x:Finisher 2", True),
    ("x:" + "a" * 30, True),
    ("x:" + "a" * 31, False),     # nombre demasiado largo
    ("x:", False),                # sin nombre
    ("x: Activación", False),     # espacio al inicio
    ("x:A,B", False),             # la coma separa el orden de los bloques
    ("x:<b>", False),
    ("strength", False),          # un bloque de siempre no es personalizado
    ("otro:Algo", False),
])
def test_cuando_una_clave_es_un_bloque_personalizado(clave, valida):
    assert es_bloque_personalizado(clave) is valida


def test_el_coach_guarda_un_bloque_con_nombre_propio_en_el_dia_de_un_atleta(coach, atleta_de_coach):
    _dia_de_atleta(coach, atleta_de_coach, LUNES)
    sesion = next(s for s in _sesiones(atleta_de_coach) if s["scheduled_date"] == str(LUNES))
    r = coach.put(f"/sessions/{sesion['id']}/meta", json={"block_notes": {"x:Activación": "10 min de movilidad"}})
    assert r.status_code == 200, r.text
    assert coach.put(f"/sessions/{sesion['id']}/meta", json={"block_order": "x:Activación,strength"}).status_code == 200

    guardada = next(s for s in _sesiones(atleta_de_coach) if s["id"] == sesion["id"])
    assert guardada["block_notes"] == {"x:Activación": "10 min de movilidad"}
    assert guardada["block_order"] == "x:Activación,strength"
    # y aparece entre los bloques del entreno, con su clave (el front le pone el nombre)
    assert "x:Activación" in next(i for i in _entrenos(coach).json() if i["kind"] == "athlete")["blocks"]


@pytest.mark.parametrize("clave", ["x:A,B", "x:" + "a" * 31, "x:", "inventado"])
def test_un_nombre_que_no_vale_se_rechaza(coach, atleta_de_coach, clave):
    _dia_de_atleta(coach, atleta_de_coach, LUNES)
    sesion = next(s for s in _sesiones(atleta_de_coach) if s["scheduled_date"] == str(LUNES))
    assert coach.put(f"/sessions/{sesion['id']}/meta", json={"block_notes": {clave: "texto"}}).status_code == 400
    assert coach.put(f"/sessions/{sesion['id']}/meta", json={"block_order": clave}).status_code == 400


def test_el_coach_escribe_un_bloque_con_nombre_propio_para_todo_el_grupo(coach, grupo):
    g, ana, beto = grupo
    dia = _dia_de_grupo(coach, g, LUNES)
    base = {"program_name": dia["program_name"], "program_start_date": dia["program_start_date"],
            "scheduled_date": dia["scheduled_date"]}
    r = coach.post(f"/groups/{g['id']}/sessions/bulk-set-block-notes",
                   json={**base, "block": "x:Finisher", "block_text": "3 rondas de burpees"})
    assert r.status_code == 200, r.text
    for atleta in (ana, beto):
        sesion = next(s for s in _sesiones(atleta) if s["scheduled_date"] == str(LUNES))
        assert sesion["block_notes"] == {"x:Finisher": "3 rondas de burpees"}
    # un texto vacío lo quita
    coach.post(f"/groups/{g['id']}/sessions/bulk-set-block-notes", json={**base, "block": "x:Finisher", "block_text": ""})
    assert next(s for s in _sesiones(ana) if s["scheduled_date"] == str(LUNES))["block_notes"] is None


def test_un_plan_guarda_bloques_con_nombre_propio_y_el_atleta_los_recibe(coach, atleta_de_coach, plantilla):
    detalle = coach.get(f"/plans/{plantilla['id']}").json()
    dia = detalle["sessions"][0]["id"]
    r = coach.put(f"/plans/{plantilla['id']}/sessions/{dia}/meta", json={
        "block_notes": {"x:Activación": "10 min de movilidad", "x:Finisher": "3 rondas de burpees"},
        "block_order": "x:Activación,metcon,strength,x:Finisher",
    })
    assert r.status_code == 200, r.text
    # un nombre inválido o un orden con un bloque inventado se rechazan
    assert coach.put(f"/plans/{plantilla['id']}/sessions/{dia}/meta", json={"block_notes": {"x:A,B": "no"}}).status_code == 400
    assert coach.put(f"/plans/{plantilla['id']}/sessions/{dia}/meta", json={"block_order": "inventado"}).status_code == 400

    en_el_plan = next(x for x in coach.get(f"/plans/{plantilla['id']}").json()["sessions"] if x["id"] == dia)
    assert en_el_plan["block_notes"] == {"x:Activación": "10 min de movilidad", "x:Finisher": "3 rondas de burpees"}

    # al asignar el plan, el atleta recibe esos bloques con su nombre y en su orden
    assert _asignar_a_atleta(coach, atleta_de_coach, plantilla).status_code == 200
    resumen = _mesociclo(atleta_de_coach)
    primera = atleta_de_coach.get(f"/mesocycles/{resumen['id']}").json()["sessions"][0]
    assert primera["block_notes"] == {"x:Activación": "10 min de movilidad", "x:Finisher": "3 rondas de burpees"}
    assert primera["block_order"] == "x:Activación,metcon,strength,x:Finisher"
