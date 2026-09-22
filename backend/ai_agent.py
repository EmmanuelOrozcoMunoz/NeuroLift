import logging
import os
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Mensaje genérico que sí es seguro devolver al cliente -- el detalle real (que puede incluir
# la URL de la petición a Gemini) se queda solo en el log del servidor. Nunca se debe propagar
# str(e) crudo en una respuesta HTTP: antes de este fix, un error de Gemini devolvía la URL
# completa de la petición -- con la API key en la query string -- directo al navegador del coach.
_MENSAJE_ERROR_GENERICO = "No se pudo generar la rutina en este momento. Intenta de nuevo."

# Errores transitorios de Gemini (hipos momentáneos del servicio, rate limiting) que vale la
# pena reintentar en vez de fallar de inmediato y obligar al usuario a repetir la acción a mano.
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 2  # por modelo — con fallback entre modelos, no conviene insistir demasiado en uno solo
_BASE_DELAY_SECONDS = 1.5
_REQUEST_TIMEOUT_SECONDS = 45

# Modelo principal (mejor calidad) primero; si está saturado o caído, se reintenta con el
# secundario en vez de fallarle la sesión al usuario. Ver adapt_session_to_time/generate_workout_session.
_MODELOS_CON_FALLBACK = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]

# Instrucción compartida por todos los prompts que generan ejercicios: cada uno debe traer un
# "block" (parte de la sesión) tomado de esta lista fija — ver backend/schemas.py:Bloque, que
# valida lo mismo del lado de los endpoints manuales, y web/src/lib/blocks.ts, que define las
# etiquetas/orden en el frontend. Si la IA devuelve otra cosa, backend/main.py:_clean_ai_block
# la descarta (mejor sin bloque que un valor inventado).
_INSTRUCCION_BLOQUES = """
Cada ejercicio debe incluir un campo "block" (en inglés, EXACTAMENTE uno de estos valores) que
indique la parte de la sesión a la que pertenece:
- "warmup": calentamiento (movilidad, activación, series de aproximación).
- "strength": fuerza tipo squat/press/deadlift y sus variantes.
- "weightlifting": weightlifting olímpico — snatch, clean & jerk y sus derivados/técnica.
- "skills": gimnasia / skills — dominadas, muscle-ups, handstand, técnica gimnástica.
- "metcon": trabajo metabólico / condicionamiento (AMRAP, EMOM, for time, intervalos).
- "accessory": accesorios, core, trabajo complementario de bajo riesgo/intensidad.
- "main": bloque principal genérico — úsalo SOLO si la disciplina NO es CrossFit y el ejercicio
  no encaja mejor en "strength" o "accessory".
Si la disciplina es CrossFit, reparte los ejercicios entre warmup/strength/weightlifting/skills/
metcon/accessory según corresponda (no uses "main"). Si NO es CrossFit, usa normalmente solo
"warmup", "strength" y, cuando aplique, "accessory" — no inventes weightlifting/skills/metcon
salvo que el ejercicio sea literalmente eso.
"""


def _post_to_gemini(url: str, payload: dict, headers: dict) -> dict:
    """POST a Gemini con reintentos automáticos (backoff exponencial: ~1.5s, 3s) ante errores
    transitorios (503 Service Unavailable, 429 rate limit, timeouts o caídas de conexión).
    Un error no-transitorio (ej. 400 por payload inválido) se relanza de inmediato, sin reintentar."""
    last_exception = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            last_exception = e
            status = getattr(e.response, "status_code", None)
            es_transitorio = status in _TRANSIENT_STATUS_CODES or status is None
            if es_transitorio and attempt < _MAX_RETRIES:
                time.sleep(_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))
                continue
            raise
    raise last_exception


def _generate_json_with_fallback(prompt: str, modelos: list[str] = _MODELOS_CON_FALLBACK) -> dict:
    """Genera contenido JSON probando cada modelo de `modelos` en orden: si el primero está
    saturado/caído (tras agotar sus reintentos), prueba automáticamente con el siguiente antes
    de darse por vencido — un modelo momentáneamente sobrecargado no debería tumbar la función."""
    api_key = os.getenv("GEMINI_API_KEY").strip()
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    # La key va en un header, nunca en la URL: una URL con `?key=...` queda embebida tal cual
    # en el mensaje de cualquier excepción de `requests` (timeouts, HTTPError, etc.), y ese
    # mensaje es exactamente lo que _generate_json_with_fallback captura y podría propagar.
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

    last_exception = None
    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
        try:
            return _post_to_gemini(url, payload, headers)
        except requests.exceptions.RequestException as e:
            last_exception = e
            continue
    raise last_exception


def generate_workout_session(athlete_name: str, discipline: str, experience_notes: str) -> dict:
    prompt = f"""
    Eres el Head Coach de IA de NeuroLift. Crea UNA sesión de entrenamiento para este atleta.
    Atleta: {athlete_name}
    Disciplina: {discipline}
    Contexto: {experience_notes}

    {_INSTRUCCION_BLOQUES}

    DEBES responder ÚNICAMENTE con un objeto JSON válido que siga exactamente esta estructura, sin texto adicional ni formato markdown:
    {{
        "session_focus": "string",
        "athlete_notes": "string",
        "exercises": [
            {{
                "exercise_name": "string",
                "block": "string",
                "prescribed_sets": int,
                "prescribed_reps": int,
                "rpe_target": int
            }}
        ]
    }}
    """

    try:
        # Preferimos gemini-3.6-flash (mejor calidad); si está saturado/caído, cae
        # automáticamente a gemini-3.5-flash-lite en vez de fallar la sesión completa.
        data = _generate_json_with_fallback(prompt)

        # Extraemos el texto de la respuesta (que ahora sabemos que es un JSON)
        raw_json_text = data["candidates"][0]["content"]["parts"][0]["text"]

        # Convertimos ese texto en un diccionario real de Python
        structured_data = json.loads(raw_json_text)
        return structured_data

    except Exception as e:
        logger.error("generate_workout_session: fallo llamando a Gemini: %s", e)
        return {"error": _MENSAJE_ERROR_GENERICO}

def generate_mesocycle_chunk(
    athlete_name: str,
    discipline: str,
    experience_notes: str,
    start_week: int,
    end_week: int,
    session_dates: list[str],
    session_duration_minutes: int | None = None,
    literatura_cientifica: str = "",
    day_focus_text: str = "",
) -> dict:
    """`literatura_cientifica` se calcula UNA sola vez por mesociclo (search_knowledge_base) y se
    pasa ya lista a cada chunk — discipline/experience_notes no cambian entre chunks del mismo
    mesociclo, así que repetir la búsqueda vectorial en cada uno era una llamada a Gemini +
    consulta a la base de datos completamente redundante."""
    # Convertimos la lista de fechas en un texto legible para Gemini
    fechas_str = ", ".join(session_dates)

    regla_duracion = ""
    if session_duration_minutes:
        regla_duracion = f"""
    REGLA DE DURACIÓN: Cada sesión debe poder completarse en aproximadamente {session_duration_minutes}
    minutos (calentamiento + parte principal + accesorios). Ajusta el número de ejercicios y de series
    totales por sesión para que quepan realistamente en ese tiempo — prioriza calidad e intensidad sobre
    volumen si el tiempo es corto.
    """

    regla_enfoque_dia = ""
    if day_focus_text:
        regla_enfoque_dia = f"""
    REGLA DE ENFOQUE POR FECHA (OBLIGATORIA): el coach pidió un enfoque específico para estas
    fechas exactas (ya son las mismas fechas de la REGLA CRÍTICA DE CALENDARIO, no hace falta que
    calcules nada) — para la sesión de cada una de estas fechas, prioriza lo que se pide:
    {day_focus_text}
    """

    prompt = f"""
    Eres el Head Coach de IA de NeuroLift. Estamos construyendo un mesociclo grande por partes.
    Genera SOLO desde la SEMANA {start_week} hasta la SEMANA {end_week} para este atleta.

    REGLA CRÍTICA DE CALENDARIO:
    El atleta entrenará EXACTAMENTE en estas fechas cronológicas: {fechas_str}
    DEBES generar exactamente {len(session_dates)} objetos de sesión en total.

    Aplica sobrecarga progresiva en estas semanas específicas.
    {regla_duracion}
    {regla_enfoque_dia}
    Basate estrictamente en los siguientes principios extraídos de nuestra base de datos si son relevantes:
    {literatura_cientifica}

    Atleta: {athlete_name}
    Disciplina: {discipline}
    Contexto y Marcas Actuales: {experience_notes}

    REGLA DE INTENSIDAD (OBLIGATORIA, no la ignores): Para CUALQUIER ejercicio que tenga una marca
    de 1RM registrada que aplique (el mismo movimiento, o uno claramente derivado — p. ej. la marca
    de Back Squat aplica a Front Squat), TIENES PROHIBIDO calcular el kg tú mismo y ponerlo en
    "prescribed_weight". En vez de eso, DEBES dejar "prescribed_weight" en null y usar
    "prescribed_percentage" + "reference_exercise".

    Ejemplo EXACTO de lo que se espera si la marca es "Back Squat: 100kg" y quieres prescribir 75%
    de esa marca para un Back Squat:
        "prescribed_weight": null,
        "prescribed_percentage": 75,
        "reference_exercise": "Back Squat"
    Esto es INCORRECTO (no lo hagas): "prescribed_weight": 75.0, "prescribed_percentage": null.

    "reference_exercise" debe ser el nombre EXACTO del ejercicio tal como aparece en "Marcas
    Actuales" arriba. El sistema calculará el kg real a partir de esa marca — así el peso se
    mantiene correcto aunque el atleta actualice su 1RM después (un kg fijo que calcules tú no se
    actualizaría solo). Usa "prescribed_weight" (un kg fijo, tu mejor estimación) ÚNICAMENTE cuando
    el ejercicio no tenga ninguna marca de 1RM relacionada para referenciar.

    {_INSTRUCCION_BLOQUES}

    DEBES responder ÚNICAMENTE con un objeto JSON válido con esta estructura, sin texto adicional:
    {{
        "mesocycle_focus": "string",
        "weeks": [
            {{
                "week_number": int (debe estar entre {start_week} y {end_week}),
                "sessions": [
                    {{
                        "scheduled_date": "YYYY-MM-DD",  <-- ¡LA IA INYECTARÁ LA FECHA AQUÍ!
                        "athlete_notes": "string",
                        "exercises": [
                            {{
                                "exercise_name": "string",
                                "block": "string",
                                "prescribed_sets": int,
                                "prescribed_reps": int,
                                "rpe_target": int,
                                "prescribed_weight": float | null,
                                "prescribed_percentage": float | null,
                                "reference_exercise": "string | null"
                            }}
                        ]
                    }}
                ]
            }}
        ]
    }}
    """

    try:
        # gemini-3.6-flash primero (sigue mejor la REGLA DE INTENSIDAD que 3.5-flash-lite, que
        # tendía a ignorarla y calcular el kg fijo de todos modos); cae a 3.5-flash-lite si está
        # saturado. Antes esta función llamaba directo a 3.5-flash-lite sin fallback ni modo JSON.
        data = _generate_json_with_fallback(prompt)
        raw_json_text = data["candidates"][0]["content"]["parts"][0]["text"]

        # Limpieza de seguridad
        raw_json_text = raw_json_text.replace("```json", "").replace("```", "").strip()

        return json.loads(raw_json_text)
    except Exception as e:
        logger.error("generate_mesocycle_chunk: fallo llamando a Gemini: %s", e)
        return {"error": _MENSAJE_ERROR_GENERICO}


def adapt_session_to_time(
    athlete_name: str,
    discipline: str,
    experience_notes: str,
    original_exercises: list[dict],
    available_minutes: int,
) -> dict:
    """Toma los ejercicios YA prescritos para una sesión y los adapta (menos series, sustituye
    o recorta ejercicios) para que quepan en `available_minutes`, manteniendo el mismo enfoque
    de entrenamiento en la medida de lo posible. La sesión original NUNCA se modifica; esto
    genera una versión alterna."""
    ejercicios_texto = "\n".join(
        f"- [{e.get('block') or 'sin bloque'}] {e['exercise_name']}: {e['prescribed_sets']}x{e['prescribed_reps']}"
        + (f" @ {e['prescribed_weight']}kg" if e.get("prescribed_weight") else "")
        + (f" (RPE {e['rpe']})" if e.get("rpe") is not None else "")
        for e in original_exercises
    )

    prompt = f"""
    Eres el Head Coach de IA de NeuroLift. Un atleta tiene programada la siguiente sesión pero
    HOY solo dispone de {available_minutes} minutos para entrenar. Adapta la sesión para que
    quepa realistamente en ese tiempo (calentamiento + parte principal), conservando en lo
    posible el mismo enfoque/estímulo de la sesión original: prioriza los ejercicios más
    importantes, reduce el número de series/ejercicios accesorios, o combina movimientos si
    hace falta.

    Atleta: {athlete_name}
    Disciplina: {discipline}
    Contexto y marcas actuales: {experience_notes}

    Sesión original prescrita (cada línea ya trae entre corchetes el bloque al que pertenece):
    {ejercicios_texto}

    {_INSTRUCCION_BLOQUES}
    Para cada ejercicio que conserves o recortes de la sesión original, usa el MISMO bloque que
    ya tenía (el que está entre corchetes arriba); solo asigna un bloque distinto si sustituyes
    el ejercicio por otro de una categoría distinta.

    DEBES responder ÚNICAMENTE con un objeto JSON válido que siga exactamente esta estructura,
    sin texto adicional ni formato markdown:
    {{
        "session_focus": "string",
        "athlete_notes": "string (menciona que es una versión adaptada a {available_minutes} minutos)",
        "exercises": [
            {{
                "exercise_name": "string",
                "block": "string",
                "prescribed_sets": int,
                "prescribed_reps": int,
                "rpe_target": int,
                "prescribed_weight": float | null
            }}
        ]
    }}
    """

    try:
        # Mismo fallback que generate_workout_session: 3.6-flash primero, 3.5-flash-lite si falla.
        data = _generate_json_with_fallback(prompt)
        raw_json_text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(raw_json_text)
    except Exception as e:
        logger.error("adapt_session_to_time: fallo llamando a Gemini: %s", e)
        return {"error": _MENSAJE_ERROR_GENERICO}
