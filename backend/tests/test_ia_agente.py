"""El cliente de Gemini (backend/ai_agent.py) con `requests.post` sustituido: nunca sale a la red."""
import json
import logging

import pytest
import requests

from backend import ai_agent
from backend.services.ai_salida import BLOQUES, FORMATOS_DE_WOD


class Respuesta:
    def __init__(self, estado, cuerpo):
        self.status_code, self._cuerpo = estado, cuerpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self):
        return self._cuerpo


def _cuerpo(texto, **extra):
    return {
        "candidates": [{"content": {"parts": [{"text": texto}]}, "finishReason": extra.pop("finishReason", "STOP")}],
        "usageMetadata": {"promptTokenCount": 1200, "candidatesTokenCount": 3400, "thoughtsTokenCount": 150, "totalTokenCount": 4750},
        **extra,
    }


@pytest.fixture
def red(monkeypatch):
    """Sustituye las llamadas a Gemini: `red.guion` es una lista de funciones (payload) -> Respuesta, una
    por llamada; `red.llamadas` guarda lo que se envió."""
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(ai_agent.time, "sleep", lambda _s: None)

    class Falsa:
        pass

    falsa = Falsa()
    falsa.llamadas, falsa.guion = [], []

    def post(url, json=None, headers=None, timeout=None):
        falsa.llamadas.append({"url": url, "payload": json, "headers": headers})
        paso = falsa.guion.pop(0) if falsa.guion else (lambda _p: Respuesta(200, _cuerpo('{"weeks": []}')))
        return paso(json)

    monkeypatch.setattr(ai_agent.requests, "post", post)
    return falsa


def _config(llamada):
    return llamada["payload"]["generationConfig"]


# ------------------------------------------------------------------ esquema formal con degradación segura

def test_con_esquema_se_pide_la_salida_estructurada(red):
    data = ai_agent._generate_json_with_fallback("hola", esquema={"type": "OBJECT"})
    assert _config(red.llamadas[0]) == {"responseMimeType": "application/json", "responseSchema": {"type": "OBJECT"}}
    assert data["_con_esquema"] is True and data["_modelo"] == ai_agent._MODELOS_CON_FALLBACK[0]


def test_sin_esquema_la_llamada_es_la_de_siempre(red):
    data = ai_agent._generate_json_with_fallback("hola")
    assert _config(red.llamadas[0]) == {"responseMimeType": "application/json"}
    assert data["_con_esquema"] is False


def test_si_gemini_rechaza_el_esquema_se_repite_la_llamada_sin_esquema(red, caplog):
    red.guion = [lambda p: Respuesta(400, {"error": "schema"}), lambda p: Respuesta(200, _cuerpo("{}"))]
    with caplog.at_level(logging.WARNING, logger=ai_agent.logger.name):
        data = ai_agent._generate_json_with_fallback("hola", esquema={"type": "OBJECT"})
    assert len(red.llamadas) == 2
    assert "responseSchema" in _config(red.llamadas[0]) and "responseSchema" not in _config(red.llamadas[1])
    assert data["_con_esquema"] is False
    assert "rechazó el esquema" in caplog.text
    # ambas llamadas fueron al MISMO modelo: un rechazo de esquema no es motivo para cambiar de modelo
    assert red.llamadas[0]["url"] == red.llamadas[1]["url"]


def test_un_400_sin_esquema_no_se_reintenta_y_pasa_al_siguiente_modelo(red):
    red.guion = [lambda p: Respuesta(400, {}), lambda p: Respuesta(200, _cuerpo("{}"))]
    data = ai_agent._generate_json_with_fallback("hola")
    assert len(red.llamadas) == 2 and data["_modelo"] == ai_agent._MODELOS_CON_FALLBACK[1]


def test_un_error_que_no_es_400_con_esquema_pasa_al_siguiente_modelo_sin_repetir_el_primero(red):
    red.guion = [lambda p: Respuesta(403, {}), lambda p: Respuesta(200, _cuerpo("{}"))]
    data = ai_agent._generate_json_with_fallback("hola", esquema={"type": "OBJECT"})
    assert len(red.llamadas) == 2
    assert "responseSchema" in _config(red.llamadas[1]) and data["_modelo"] == ai_agent._MODELOS_CON_FALLBACK[1]


def test_si_todos_los_modelos_fallan_se_lanza_el_ultimo_error(red):
    red.guion = [lambda p: Respuesta(403, {})] * 10
    with pytest.raises(requests.exceptions.RequestException):
        ai_agent._generate_json_with_fallback("hola", esquema={"type": "OBJECT"})


def test_la_clave_de_gemini_viaja_en_un_header_nunca_en_la_url(red):
    ai_agent._generate_json_with_fallback("hola")
    llamada = red.llamadas[0]
    assert llamada["headers"]["x-goog-api-key"] == "clave-de-prueba" and "clave-de-prueba" not in llamada["url"]


# ------------------------------------------------------------------ el esquema mismo

def test_el_esquema_exige_solo_valores_que_la_app_acepta():
    esquema = ai_agent.esquema_mesociclo()
    sesion = esquema["properties"]["weeks"]["items"]["properties"]["sessions"]["items"]
    props = sesion["properties"]
    assert set(props) >= {"scheduled_date", "athlete_notes", "warmup_notes", "block_order", "wod", "exercises"}
    ejercicio = props["exercises"]["items"]["properties"]
    assert set(ejercicio) >= {"exercise_name", "block", "prescribed_sets", "prescribed_reps", "rpe_target", "prescribed_weight",
                              "prescribed_percentage", "reference_exercise", "coach_note", "series"}
    assert ejercicio["block"]["enum"] == list(BLOQUES)
    assert props["wod"]["properties"]["format"]["enum"] == list(FORMATOS_DE_WOD) and len(FORMATOS_DE_WOD) == 9
    assert props["block_order"]["items"]["enum"] == list(BLOQUES)
    assert sesion["required"] == ["scheduled_date", "exercises"]


def test_el_esquema_solo_usa_palabras_que_gemini_documenta():
    """Un 400 por una palabra no soportada degradaría TODA llamada a "sin esquema": se vigila."""
    permitidas = {"type", "properties", "required", "items", "enum", "nullable", "description"}

    def revisar(nodo):
        if isinstance(nodo, dict):
            if "type" in nodo:   # un esquema (no el diccionario `properties`, cuyas llaves son nombres de campo)
                assert set(nodo) <= permitidas, set(nodo) - permitidas
            for clave, valor in nodo.items():
                revisar(valor if clave != "properties" else {"": None, **{k: v for k, v in valor.items()}})
        elif isinstance(nodo, list):
            for item in nodo:
                revisar(item)

    for esquema in (ai_agent.esquema_mesociclo(), ai_agent.esquema_sesion_suelta()):
        revisar(esquema)
        json.dumps(esquema)   # es serializable


# ------------------------------------------------------------------ uso de tokens

def test_extraer_uso_lee_los_tokens_de_la_respuesta():
    uso = ai_agent._extraer_uso({**_cuerpo("{}"), "_modelo": "m", "_con_esquema": True})
    assert uso == {"modelo": "m", "con_esquema": True, "tokens_prompt": 1200, "tokens_salida": 3400, "tokens_pensamiento": 150, "tokens_total": 4750}
    vacio = ai_agent._extraer_uso({"candidates": []})
    assert vacio["tokens_total"] == 0 and vacio["modelo"] is None
    assert ai_agent._extraer_uso(None)["tokens_prompt"] == 0
    assert ai_agent._extraer_uso({"usageMetadata": {"promptTokenCount": "mucho"}})["tokens_prompt"] == 0


def test_cada_generacion_registra_los_tokens_en_el_log(red, caplog):
    red.guion = [lambda p: Respuesta(200, _cuerpo(json.dumps({"weeks": []})))]
    with caplog.at_level(logging.INFO, logger=ai_agent.logger.name):
        resultado = ai_agent.generate_mesocycle_chunk(
            athlete_name="Ana", discipline="CrossFit", experience_notes="x", start_week=1, end_week=3,
            session_dates=["2026-01-05"],
        )
    assert resultado["_uso"]["tokens_salida"] == 3400 and resultado["_uso"]["con_esquema"] is True
    assert "semanas 1-3" in caplog.text and "entrada=1200" in caplog.text and "salida=3400" in caplog.text


# ------------------------------------------------------------------ lo que devuelve la generación

def test_generate_mesocycle_chunk_devuelve_el_json_y_tolera_las_vallas_de_markdown(red):
    red.guion = [lambda p: Respuesta(200, _cuerpo('```json\n{"weeks": [{"sessions": []}]}\n```'))]
    r = ai_agent.generate_mesocycle_chunk(athlete_name="Ana", discipline="CrossFit", experience_notes="x", start_week=1, end_week=1, session_dates=["2026-01-05"])
    assert r["weeks"] == [{"sessions": []}] and "error" not in r


def test_una_salida_cortada_por_limite_de_tokens_se_avisa_y_falla_con_el_mensaje_generico(red, caplog):
    red.guion = [lambda p: Respuesta(200, _cuerpo('{"weeks": [{"sessions": [{"scheduled_da', finishReason="MAX_TOKENS"))]
    with caplog.at_level(logging.WARNING, logger=ai_agent.logger.name):
        r = ai_agent.generate_mesocycle_chunk(athlete_name="Ana", discipline="CrossFit", experience_notes="x", start_week=1, end_week=1, session_dates=["2026-01-05"])
    assert r == {"error": ai_agent._MENSAJE_ERROR_GENERICO}
    assert "límite de tokens" in caplog.text


def test_un_fallo_de_gemini_no_filtra_la_clave_ni_la_url(red):
    red.guion = [lambda p: Respuesta(500, {})] * 10
    r = ai_agent.generate_mesocycle_chunk(athlete_name="Ana", discipline="CrossFit", experience_notes="x", start_week=1, end_week=1, session_dates=["2026-01-05"])
    assert r == {"error": ai_agent._MENSAJE_ERROR_GENERICO} and "clave-de-prueba" not in json.dumps(r)


# ------------------------------------------------------------------ el prompt

def _prompt_de_chunk(red, **extra):
    ai_agent.generate_mesocycle_chunk(
        athlete_name="Ana", discipline="CrossFit", experience_notes="Marcas: Back Squat 100kg", start_week=1, end_week=3,
        session_dates=["2026-01-05", "2026-01-07"], **extra,
    )
    return red.llamadas[0]["payload"]["contents"][0]["parts"][0]["text"]


def test_el_prompt_pide_todos_los_componentes_de_la_sesion(red):
    prompt = _prompt_de_chunk(red)
    for componente in ("warmup_notes", "block_order", "coach_note", '"series"', "rampas"):
        assert componente in prompt, componente
    for formato in FORMATOS_DE_WOD:
        assert f'"{formato}"' in prompt, formato
    assert "Clean & Jerk" in prompt and "Back Squat" in prompt  # los nombres estándar de los levantamientos


def test_el_prompt_prohibe_inventar_un_kg_sin_marca_en_un_levantamiento(red):
    prompt = _prompt_de_chunk(red)
    assert "NO inventes un kg" in prompt and "PLANTILLA" in prompt   # y la excepción de las plantillas
    assert "TIENES PROHIBIDO" in prompt and "prescribed_percentage" in prompt


def test_el_prompt_pide_una_sesion_por_fecha_exacta_y_mantiene_la_proteccion_anti_inyeccion(red):
    prompt = _prompt_de_chunk(red, day_focus_text="- 2026-01-05 (Lunes): Piernas")
    assert "2026-01-05, 2026-01-07" in prompt and "exactamente 2 objetos de sesión" in prompt
    assert 'untrusted="true"' in prompt and "Piernas" in prompt


def test_la_sesion_suelta_tambien_usa_el_esquema_y_los_componentes(red):
    red.guion = [lambda p: Respuesta(200, _cuerpo(json.dumps({"session_focus": "x", "exercises": []})))]
    r = ai_agent.generate_workout_session("Ana", "CrossFit", "contexto")
    assert "responseSchema" in _config(red.llamadas[0]) and r["session_focus"] == "x" and r["_uso"]["tokens_prompt"] == 1200
    assert "warmup_notes" in red.llamadas[0]["payload"]["contents"][0]["parts"][0]["text"]
