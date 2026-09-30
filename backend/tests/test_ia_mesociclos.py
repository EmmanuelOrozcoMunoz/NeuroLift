"""Generación con IA: la llamada a Gemini se simula; se prueba lo que hace NeuroLift con la respuesta."""
from datetime import date, timedelta

import pytest

HOY = date.today()


@pytest.fixture
def gemini(monkeypatch):
    """Sustituye las llamadas a Gemini por una función controlable. `gemini.ejercicios` define qué
    devuelve para cada fecha, `gemini.llamadas` guarda lo que se le pidió y `gemini.error` la hace fallar."""
    from backend import ai_agent, knowledge_search

    class Falso:
        pass

    falso = Falso()
    falso.llamadas = []
    falso.error = None
    falso.wod = None   # el WOD que devuelve la IA en cada sesión (None = sin WOD)
    falso.ejercicios = [
        {"exercise_name": "Back Squat", "prescribed_sets": 3, "prescribed_reps": 5, "rpe_target": 8,
         "prescribed_percentage": 80, "block": "strength"}
    ]

    def chunk(**kw):
        falso.llamadas.append(kw)
        if falso.error:
            raise RuntimeError(falso.error)
        return {"weeks": [{"sessions": [
            {"scheduled_date": f, "athlete_notes": "IA", "wod": falso.wod, "exercises": [dict(e) for e in falso.ejercicios]}
            for f in kw["session_dates"]
        ]}]}

    monkeypatch.setattr(ai_agent, "generate_mesocycle_chunk", chunk)
    monkeypatch.setattr(knowledge_search, "search_knowledge_base", lambda _ctx: "literatura")
    return falso


def _pedir(coach, atleta, **extra):
    cuerpo = {
        "user_id": atleta.id, "name": "Bloque IA", "discipline": "CrossFit", "start_date": str(HOY),
        "weeks_count": 2, "training_days": [HOY.weekday()], "context": "", **extra,
    }
    return coach.post("/ai/generate-smart-mesocycle/", json=cuerpo)


def _series_del_atleta(coach, atleta):
    meso = next(m for m in coach.get(f"/users/{atleta.id}/mesocycles/").json() if m["name"] == "Bloque IA")
    sesiones = coach.get(f"/mesocycles/{meso['id']}").json()["sessions"]
    return meso, sesiones, [s for ses in sesiones for s in ses["sets"]]


def test_crea_las_sesiones_de_las_fechas_pedidas_y_las_series_de_cada_ejercicio(coach, atleta_de_coach, gemini):
    r = _pedir(coach, atleta_de_coach)
    assert r.status_code == 200, r.text
    meso, sesiones, series = _series_del_atleta(coach, atleta_de_coach)
    assert sorted(s["scheduled_date"] for s in sesiones) == [str(HOY), str(HOY + timedelta(days=7))]
    assert len(series) == 6  # 2 sesiones x 3 series
    assert {s["block"] for s in series} == {"strength"} and {s["rpe"] for s in series} == {8}
    assert meso["end_date"] == str(HOY + timedelta(days=7))


def test_el_porcentaje_se_resuelve_con_la_marca_actual_del_atleta(coach, atleta_de_coach, gemini):
    atleta_de_coach.post(f"/users/{atleta_de_coach.id}/records/", json={"exercise_name": "Back Squat", "max_weight_kg": 100})
    assert _pedir(coach, atleta_de_coach).status_code == 200
    _, _, series = _series_del_atleta(coach, atleta_de_coach)
    assert {(s["prescribed_weight"], s["prescribed_percentage"], s["reference_exercise"]) for s in series} == {(80, 80, "Back Squat")}


def test_un_kg_fijo_que_coincide_con_una_marca_se_convierte_en_porcentaje(coach, atleta_de_coach, gemini):
    atleta_de_coach.post(f"/users/{atleta_de_coach.id}/records/", json={"exercise_name": "Deadlift", "max_weight_kg": 150})
    gemini.ejercicios = [{"exercise_name": "Deadlift", "prescribed_sets": 1, "prescribed_reps": 3, "prescribed_weight": 120}]
    assert _pedir(coach, atleta_de_coach).status_code == 200
    _, _, series = _series_del_atleta(coach, atleta_de_coach)
    assert {(s["prescribed_weight"], s["prescribed_percentage"]) for s in series} == {(120, 80)}


def test_valores_raros_de_la_ia_no_rompen_la_generacion(coach, atleta_de_coach, gemini):
    gemini.ejercicios = [{"exercise_name": "Push-up", "prescribed_sets": 2, "prescribed_reps": 10,
                          "prescribed_weight": "mucho", "prescribed_percentage": "n/a", "rpe": "7.9", "block": "inventado"}]
    assert _pedir(coach, atleta_de_coach).status_code == 200
    _, _, series = _series_del_atleta(coach, atleta_de_coach)
    assert len(series) == 4
    assert {(s["prescribed_weight"], s["prescribed_percentage"], s["rpe"]) for s in series} == {(None, None, 7)}
    assert {s["block"] for s in series} == {None}  # un bloque que no existe se descarta


def test_un_mesociclo_largo_se_pide_en_tandas_de_tres_semanas(coach, atleta_de_coach, gemini):
    assert _pedir(coach, atleta_de_coach, weeks_count=7).status_code == 200
    semanas = sorted((c["start_week"], c["end_week"]) for c in gemini.llamadas)
    assert semanas == [(1, 3), (4, 6), (7, 7)]


def test_la_guia_por_dia_viaja_atada_a_la_fecha(coach, atleta_de_coach, gemini):
    dia = HOY.weekday()
    assert _pedir(coach, atleta_de_coach, weeks_count=1, day_focus={str(dia): "Sentadilla pesada"}).status_code == 200
    texto = gemini.llamadas[0]["day_focus_text"]
    assert str(HOY) in texto and "Sentadilla pesada" in texto


def test_si_la_ia_falla_no_queda_un_mesociclo_a_medias(coach, atleta_de_coach, gemini):
    gemini.error = "Gemini caído"
    r = _pedir(coach, atleta_de_coach)
    assert r.status_code == 500 and "Gemini caído" in r.text
    assert all(m["name"] != "Bloque IA" for m in coach.get(f"/users/{atleta_de_coach.id}/mesocycles/").json())


def test_solo_el_coach_del_atleta_puede_generar(coach, atleta_solo, gemini):
    assert _pedir(coach, atleta_solo).status_code in (403, 404)


def test_generacion_para_un_grupo_arma_un_mesociclo_por_atleta(client, coach, atleta_de_coach, codigo_coach, gemini):
    from backend.tests.conftest import Cuenta

    email = f"grupal-{atleta_de_coach.id[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "full_name": "Segundo", "password": "password123", "invite_code": codigo_coach})
    token = client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]
    segundo = Cuenta(client, email, token, client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json())

    grupo = coach.post("/groups/", json={"name": "IA grupal", "athlete_ids": [atleta_de_coach.id, segundo.id]}).json()
    r = coach.post("/ai/generate-smart-mesocycle/group", json={
        "group_id": grupo["id"], "name": "Bloque IA", "discipline": "CrossFit", "start_date": str(HOY),
        "weeks_count": 1, "training_days": [HOY.weekday()], "context": "",
    })
    assert r.status_code == 200, r.text
    assert sorted(x["status"] for x in r.json()["results"]) == ["success", "success"]
    for atleta in (atleta_de_coach, segundo):
        assert any(m["name"] == "Bloque IA" for m in coach.get(f"/users/{atleta.id}/mesocycles/").json())


def test_generar_una_sesion_suelta(coach, atleta_de_coach, monkeypatch):
    from backend import ai_agent

    monkeypatch.setattr(ai_agent, "generate_workout_session", lambda **kw: {
        "session_focus": "Fuerza", "athlete_notes": "Vamos",
        "exercises": [{"exercise_name": "Press", "prescribed_reps": 5, "rpe_target": 7}],
    })
    creado = coach.post("/mesocycles/manual", json={
        "user_id": atleta_de_coach.id, "name": "Base", "discipline": "CrossFit",
        "start_date": str(HOY), "weeks_count": 1, "training_days": [HOY.weekday()],
    }).json()
    r = coach.post("/ai/generate-session/", json={"mesocycle_id": creado["mesocycle_id"], "context": "fuerza", "weeks_count": 1, "sessions_per_week": 1})
    assert r.status_code == 200, r.text
    assert r.json()["session_focus"] == "Fuerza"

    monkeypatch.setattr(ai_agent, "generate_workout_session", lambda **kw: {"error": "sin cuota"})
    assert coach.post("/ai/generate-session/", json={"mesocycle_id": creado["mesocycle_id"], "context": "fuerza", "weeks_count": 1, "sessions_per_week": 1}).status_code == 500


def test_el_wod_de_la_ia_usa_la_plantilla_de_wod_y_configura_el_temporizador(coach, atleta_de_coach, gemini):
    gemini.ejercicios = []
    gemini.wod = {"name": "Fran", "format": "for_time", "time_cap_minutes": 10, "description": "21-15-9 Thrusters y Pull-ups"}
    assert _pedir(coach, atleta_de_coach, weeks_count=1).status_code == 200
    _, sesiones, series = _series_del_atleta(coach, atleta_de_coach)
    assert len(sesiones) == 1 and series == []                       # el WOD no se guardó como ejercicios sueltos
    sesion = sesiones[0]
    assert sesion["wod_format"] == "for_time"                        # plantilla de WOD: formato
    assert sesion["wod_time_cap_seconds"] == 600                     # ... y tiempo límite: de aquí sale el timer
    assert "21-15-9 Thrusters y Pull-ups" in sesion["wod_notes"] and sesion["wod_notes"].startswith("Fran")


def test_un_wod_invalido_de_la_ia_no_rompe_la_generacion_ni_deja_un_timer_a_medias(coach, atleta_de_coach, gemini):
    gemini.wod = {"name": "???", "format": "inventado", "time_cap_minutes": "mucho"}
    assert _pedir(coach, atleta_de_coach, weeks_count=1).status_code == 200
    sesion = _series_del_atleta(coach, atleta_de_coach)[1][0]
    assert sesion["wod_format"] is None and sesion["wod_time_cap_seconds"] is None


def test_la_sesion_suelta_generada_con_ia_tambien_trae_su_wod(coach, atleta_de_coach, monkeypatch):
    from backend import ai_agent

    monkeypatch.setattr(ai_agent, "generate_workout_session", lambda **kw: {
        "session_focus": "Metabólico", "athlete_notes": "Vamos",
        "wod": {"name": "Cindy", "format": "amrap", "time_cap_minutes": 20, "description": "5 pull-ups, 10 push-ups, 15 squats"},
        "exercises": [{"exercise_name": "Back Squat", "prescribed_reps": 5, "rpe_target": 7, "block": "strength"}],
    })
    creado = coach.post("/mesocycles/manual", json={
        "user_id": atleta_de_coach.id, "name": "Base", "discipline": "CrossFit",
        "start_date": str(HOY), "weeks_count": 1, "training_days": [HOY.weekday()],
    }).json()
    r = coach.post("/ai/generate-session/", json={"mesocycle_id": creado["mesocycle_id"], "context": "x", "weeks_count": 1, "sessions_per_week": 1})
    assert r.status_code == 200, r.text
    sesiones = coach.get(f"/mesocycles/{creado['mesocycle_id']}").json()["sessions"]
    con_wod = [s for s in sesiones if s["wod_format"]]
    assert len(con_wod) == 1 and con_wod[0]["wod_format"] == "amrap" and con_wod[0]["wod_time_cap_seconds"] == 1200
