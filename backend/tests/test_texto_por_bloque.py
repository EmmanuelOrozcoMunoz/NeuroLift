"""Texto libre por bloque: el coach programa cada bloque de un día como un bloc de notas
(`Session.block_notes`), sin estructurarlo en ejercicios y series. Se copia al asignar un plan y se
puede escribir de una vez para todo un grupo."""
from datetime import date

import pytest

from backend.tests.test_asignar_plan import (  # noqa: F401  (fixtures y ayudas)
    SALIDA,
    _asignar,
    _mesociclo,
    grupo,
    plantilla,
)

HOY = date.today()


def _sesion_manual(coach, atleta):
    """Una sesión sin ejercicios, de un mesociclo manual del atleta."""
    r = coach.post("/mesocycles/manual", json={
        "user_id": atleta.id, "name": "Manual", "discipline": "CrossFit",
        "start_date": str(HOY), "weeks_count": 1, "training_days": [HOY.weekday()],
    })
    assert r.status_code == 200, r.text
    meso = next(m for m in coach.get(f"/users/{atleta.id}/mesocycles/").json() if m["name"] == "Manual")
    return meso["id"], coach.get(f"/mesocycles/{meso['id']}").json()["sessions"][0]


def _escribir(cuenta, sesion_id, notas):
    return cuenta.put(f"/sessions/{sesion_id}/meta", json={"block_notes": notas})


# ------------------------------------------------------------------ una sesión

def test_el_coach_escribe_un_texto_por_bloque_y_conserva_los_saltos_de_linea(coach, atleta_de_coach):
    _, sesion = _sesion_manual(coach, atleta_de_coach)
    texto = "Back Squat 5x5 @80%\nPress de banca 4x6\n  descanso 2 min"
    r = _escribir(coach, sesion["id"], {"strength": texto, "accessory": "Remo 3x10"})
    assert r.status_code == 200, r.text
    notas = r.json()["block_notes"]
    assert notas["strength"] == "Back Squat 5x5 @80%\nPress de banca 4x6\ndescanso 2 min"
    assert notas["accessory"] == "Remo 3x10"


def test_escribir_un_bloque_no_borra_los_demas_y_un_texto_vacio_lo_quita(coach, atleta_de_coach):
    _, sesion = _sesion_manual(coach, atleta_de_coach)
    _escribir(coach, sesion["id"], {"strength": "Sentadilla", "skills": "Dominadas"})
    r = _escribir(coach, sesion["id"], {"skills": "Muscle-ups"})
    assert r.json()["block_notes"] == {"strength": "Sentadilla", "skills": "Muscle-ups"}
    r = _escribir(coach, sesion["id"], {"strength": "   "})
    assert r.json()["block_notes"] == {"skills": "Muscle-ups"}
    r = _escribir(coach, sesion["id"], {"skills": ""})
    assert r.json()["block_notes"] is None


def test_un_meta_sin_block_notes_no_los_toca(coach, atleta_de_coach):
    _, sesion = _sesion_manual(coach, atleta_de_coach)
    _escribir(coach, sesion["id"], {"strength": "Sentadilla"})
    r = coach.put(f"/sessions/{sesion['id']}/meta", json={"warmup_notes": "Movilidad"})
    assert r.status_code == 200 and r.json()["block_notes"] == {"strength": "Sentadilla"}


@pytest.mark.parametrize("bloque", ["warmup", "metcon", "inventado", ""])
def test_un_bloque_que_no_admite_texto_se_rechaza(coach, atleta_de_coach, bloque):
    _, sesion = _sesion_manual(coach, atleta_de_coach)
    r = _escribir(coach, sesion["id"], {bloque: "texto"})
    assert r.status_code == 400, r.text
    assert coach.get(f"/mesocycles/{sesion['mesocycle_id']}").json()["sessions"][0]["block_notes"] is None


def test_los_valores_que_no_son_texto_se_rechazan(coach, atleta_de_coach):
    _, sesion = _sesion_manual(coach, atleta_de_coach)
    assert _escribir(coach, sesion["id"], {"strength": 123}).status_code == 422
    assert _escribir(coach, sesion["id"], ["strength"]).status_code == 422


def test_el_html_se_limpia_y_el_texto_largo_se_acota(coach, atleta_de_coach):
    _, sesion = _sesion_manual(coach, atleta_de_coach)
    r = _escribir(coach, sesion["id"], {"strength": "<script>alert(1)</script>Sentadilla <b>5x5</b>"})
    assert r.status_code == 200
    assert "<" not in r.json()["block_notes"]["strength"] and "Sentadilla" in r.json()["block_notes"]["strength"]
    r = _escribir(coach, sesion["id"], {"accessory": "x" * 5000})
    assert r.status_code == 200 and len(r.json()["block_notes"]["accessory"]) <= 2000


def test_el_atleta_ve_el_texto_y_puede_terminar_una_sesion_sin_ejercicios(coach, atleta_de_coach):
    meso_id, sesion = _sesion_manual(coach, atleta_de_coach)
    _escribir(coach, sesion["id"], {"strength": "Sentadilla 5x5"})
    visto = atleta_de_coach.get(f"/mesocycles/{meso_id}").json()["sessions"][0]
    assert visto["block_notes"] == {"strength": "Sentadilla 5x5"} and visto["sets"] == []
    assert atleta_de_coach.post(f"/sessions/{sesion['id']}/complete").status_code == 200
    assert atleta_de_coach.get(f"/mesocycles/{meso_id}").json()["sessions"][0]["status"] == "completed"


def test_el_atleta_no_puede_escribir_en_lo_que_programo_su_coach(coach, atleta_de_coach):
    _, sesion = _sesion_manual(coach, atleta_de_coach)
    assert _escribir(atleta_de_coach, sesion["id"], {"strength": "lo cambio yo"}).status_code == 403


def test_otro_coach_no_puede_escribir_en_la_sesion_ajena(coach, atleta_de_coach, dueno_de_box):
    _, sesion = _sesion_manual(coach, atleta_de_coach)
    assert _escribir(dueno_de_box, sesion["id"], {"strength": "intruso"}).status_code in (403, 404)


# ------------------------------------------------------------------ planes

def _primer_dia(coach, plan):
    return sorted(coach.get(f"/plans/{plan['id']}").json()["sessions"], key=lambda s: s["day_offset"])[0]


def test_un_dia_de_plan_guarda_su_texto_por_bloque(coach, plantilla):
    dia = _primer_dia(coach, plantilla)
    r = coach.put(f"/plans/{plantilla['id']}/sessions/{dia['id']}/meta", json={"block_notes": {"strength": "Sentadilla 5x5"}})
    assert r.status_code == 200, r.text
    assert _primer_dia(coach, plantilla)["block_notes"] == {"strength": "Sentadilla 5x5"}
    r = coach.put(f"/plans/{plantilla['id']}/sessions/{dia['id']}/meta", json={"block_notes": {"warmup": "x"}})
    assert r.status_code == 400


def test_al_asignar_un_plan_el_texto_por_bloque_llega_a_cada_atleta_como_copia(coach, grupo, plantilla):
    g, ana, beto = grupo
    dia = _primer_dia(coach, plantilla)
    coach.put(f"/plans/{plantilla['id']}/sessions/{dia['id']}/meta", json={"block_notes": {"accessory": "Remo 3x10"}})
    assert _asignar(coach, g, plantilla).status_code == 200

    for atleta in (ana, beto):
        meso = atleta.get(f"/mesocycles/{_mesociclo(atleta)['id']}").json()
        con_texto = [s for s in meso["sessions"] if s["block_notes"]]
        assert [s["block_notes"] for s in con_texto] == [{"accessory": "Remo 3x10"}]

    # una copia: cambiar la de un atleta no toca la del plan ni la del otro
    meso_ana = ana.get(f"/mesocycles/{_mesociclo(ana)['id']}").json()
    sesion_ana = next(s for s in meso_ana["sessions"] if s["block_notes"])
    assert _escribir(coach, sesion_ana["id"], {"accessory": "Solo para Ana"}).status_code == 200
    assert _primer_dia(coach, plantilla)["block_notes"] == {"accessory": "Remo 3x10"}
    meso_beto = beto.get(f"/mesocycles/{_mesociclo(beto)['id']}").json()
    assert next(s for s in meso_beto["sessions"] if s["block_notes"])["block_notes"] == {"accessory": "Remo 3x10"}


# ------------------------------------------------------------------ grupo

def _para_el_grupo(coach, g, bloque, texto, fecha=SALIDA):
    return coach.post(f"/groups/{g['id']}/sessions/bulk-set-block-notes", json={
        "program_name": "Fuerza base", "program_start_date": str(SALIDA), "scheduled_date": str(fecha),
        "block": bloque, "block_text": texto,
    })


def test_el_coach_escribe_un_bloque_una_vez_para_todo_el_grupo(coach, grupo, plantilla):
    g, ana, beto = grupo
    assert _asignar(coach, g, plantilla).status_code == 200
    r = _para_el_grupo(coach, g, "strength", "Sentadilla 5x5\nPress 4x6")
    assert r.status_code == 200, r.text
    assert [x["status"] for x in r.json()["results"]] == ["actualizado", "actualizado"]

    for atleta in (ana, beto):
        meso = atleta.get(f"/mesocycles/{_mesociclo(atleta)['id']}").json()
        sesion = next(s for s in meso["sessions"] if s["scheduled_date"] == str(SALIDA))
        assert sesion["block_notes"] == {"strength": "Sentadilla 5x5\nPress 4x6"}

    # un texto vacío lo quita para todos
    assert _para_el_grupo(coach, g, "strength", "").status_code == 200
    meso = ana.get(f"/mesocycles/{_mesociclo(ana)['id']}").json()
    assert next(s for s in meso["sessions"] if s["scheduled_date"] == str(SALIDA))["block_notes"] is None


def test_en_el_grupo_un_bloque_invalido_no_guarda_nada_y_una_fecha_sin_sesion_se_avisa(coach, grupo, plantilla):
    g, ana, _ = grupo
    assert _asignar(coach, g, plantilla).status_code == 200
    assert _para_el_grupo(coach, g, "metcon", "x").status_code == 400
    meso = ana.get(f"/mesocycles/{_mesociclo(ana)['id']}").json()
    assert all(s["block_notes"] is None for s in meso["sessions"])
    r = _para_el_grupo(coach, g, "strength", "x", fecha=date(2031, 1, 1))
    assert r.status_code == 200 and {x["status"] for x in r.json()["results"]} == {"sin sesión en esa fecha"}


def test_otro_coach_no_puede_escribir_en_el_grupo_ajeno(coach, grupo, plantilla, dueno_de_box):
    g, *_ = grupo
    assert _asignar(coach, g, plantilla).status_code == 200
    assert _para_el_grupo(dueno_de_box, g, "strength", "intruso").status_code in (403, 404)


def test_el_calentamiento_tambien_se_escribe_para_todo_el_grupo(coach, grupo, plantilla):
    g, ana, beto = grupo
    assert _asignar(coach, g, plantilla).status_code == 200
    r = _para_el_grupo(coach, g, "warmup", "5 min de remo\nMovilidad de cadera")
    assert r.status_code == 200, r.text
    for atleta in (ana, beto):
        meso = atleta.get(f"/mesocycles/{_mesociclo(atleta)['id']}").json()
        sesion = next(s for s in meso["sessions"] if s["scheduled_date"] == str(SALIDA))
        assert sesion["warmup_notes"] == "5 min de remo\nMovilidad de cadera" and sesion["block_notes"] is None
    assert _para_el_grupo(coach, g, "warmup", "").status_code == 200
    meso = ana.get(f"/mesocycles/{_mesociclo(ana)['id']}").json()
    assert next(s for s in meso["sessions"] if s["scheduled_date"] == str(SALIDA))["warmup_notes"] is None
    # el WOD sigue teniendo su propia ruta: aquí no se acepta
    assert _para_el_grupo(coach, g, "metcon", "x").status_code == 400


# ------------------------------------------------------------------ entrenos propios del atleta

def test_el_atleta_escribe_el_texto_de_sus_propios_entrenos_y_los_termina(atleta_de_coach):
    r = atleta_de_coach.post("/users/me/personal-sessions", json={"scheduled_date": str(HOY)})
    assert r.status_code == 200, r.text
    sesion = r.json()
    r = _escribir(atleta_de_coach, sesion["id"], {"strength": "Sentadilla 5x5", "accessory": "Remo 3x10"})
    assert r.status_code == 200, r.text
    assert r.json()["block_notes"] == {"strength": "Sentadilla 5x5", "accessory": "Remo 3x10"}
    # un bloque sin texto permitido sigue rechazado, también para el atleta
    assert _escribir(atleta_de_coach, sesion["id"], {"metcon": "x"}).status_code == 400
    assert atleta_de_coach.post(f"/sessions/{sesion['id']}/complete").status_code == 200
    visto = atleta_de_coach.get(f"/mesocycles/{sesion['mesocycle_id']}").json()["sessions"][0]
    assert visto["status"] == "completed" and visto["block_notes"]["strength"] == "Sentadilla 5x5"
