import os
import time
import requests
import json
from dotenv import load_dotenv
from sqlalchemy import text
from backend.database import SessionLocal # Importamos tu conexión a la BD

load_dotenv()

# Errores transitorios de Gemini (hipos momentáneos del servicio, rate limiting) que vale la
# pena reintentar en vez de fallar de inmediato y obligar al usuario a repetir la acción a mano.
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 2  # por modelo — con fallback entre modelos, no conviene insistir demasiado en uno solo
_BASE_DELAY_SECONDS = 1.5
_REQUEST_TIMEOUT_SECONDS = 45

# Modelo principal (mejor calidad) primero; si está saturado o caído, se reintenta con el
# secundario en vez de fallarle la sesión al usuario. Ver adapt_session_to_time/generate_workout_session.
_MODELOS_CON_FALLBACK = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]


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
    headers = {"Content-Type": "application/json"}

    last_exception = None
    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
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

    DEBES responder ÚNICAMENTE con un objeto JSON válido que siga exactamente esta estructura, sin texto adicional ni formato markdown:
    {{
        "session_focus": "string",
        "athlete_notes": "string",
        "exercises": [
            {{
                "exercise_name": "string",
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
        return {"error": str(e)}

def search_knowledge_base(user_context: str) -> str:
    """Busca en el PDF inyectado los párrafos más relevantes para el atleta."""
    api_key = os.getenv("GEMINI_API_KEY").strip()
    embed_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={api_key}"

    try:
        # 1. Convertimos lo que pide el usuario en un vector matemático
        payload = {"model": "models/gemini-embedding-001", "content": {"parts": [{"text": user_context}]}}
        headers = {'Content-Type': 'application/json'}
        data = _post_to_gemini(embed_url, payload, headers)
        vector_busqueda = data["embedding"]["values"]

        # 2. Buscamos en PostgreSQL los 3 fragmentos más parecidos (Similitud del Coseno)
        db = SessionLocal()
        query = text("""
            SELECT content
            FROM knowledge_base
            ORDER BY embedding <=> CAST(:vector AS vector)
            LIMIT 3
        """)
        resultados = db.execute(query, {"vector": str(vector_busqueda)}).fetchall()
        db.close()

        # 3. Unimos los fragmentos en un solo texto
        if resultados:
            contexto_extra = "\n\n".join([row[0] for row in resultados])
            return f"\n--- LITERATURA DE REFERENCIA ENCONTRADA ---\n{contexto_extra}\n-------------------------------------------\n"
        return ""

    except Exception as e:
        print(f"Error en búsqueda vectorial: {e}")
        return "" # Si falla, simplemente devolvemos texto vacío y la IA sigue normal


def generate_mesocycle_chunk(athlete_name: str, discipline: str, experience_notes: str, start_week: int, end_week: int, session_dates: list[str], session_duration_minutes: int | None = None) -> dict:
    api_key = os.getenv("GEMINI_API_KEY").strip()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"

    # Tu sistema RAG intacto
    literatura_cientifica = search_knowledge_base(f"{discipline} - {experience_notes}")

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

    prompt = f"""
    Eres el Head Coach de IA de NeuroLift. Estamos construyendo un mesociclo grande por partes.
    Genera SOLO desde la SEMANA {start_week} hasta la SEMANA {end_week} para este atleta.

    REGLA CRÍTICA DE CALENDARIO:
    El atleta entrenará EXACTAMENTE en estas fechas cronológicas: {fechas_str}
    DEBES generar exactamente {len(session_dates)} objetos de sesión en total.

    Aplica sobrecarga progresiva en estas semanas específicas.
    {regla_duracion}
    Basate estrictamente en los siguientes principios extraídos de nuestra base de datos si son relevantes:
    {literatura_cientifica}

    Atleta: {athlete_name}
    Disciplina: {discipline}
    Contexto y Marcas Actuales: {experience_notes}

    REGLA DE INTENSIDAD: Si el atleta tiene marcas de 1RM registradas, DEBES calcular los pesos exactos en kilogramos para sus series según la intensidad que programes, e incluir el peso exacto dentro del campo 'athlete_notes' de cada sesión o en las repeticiones.

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
                                "prescribed_sets": int,
                                "prescribed_reps": int,
                                "rpe_target": int,
                                "prescribed_weight": float | null
                            }}
                        ]
                    }}
                ]
            }}
        ]
    }}
    """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}

    try:
        data = _post_to_gemini(url, payload, headers)
        raw_json_text = data["candidates"][0]["content"]["parts"][0]["text"]

        # Limpieza de seguridad
        raw_json_text = raw_json_text.replace("```json", "").replace("```", "").strip()

        return json.loads(raw_json_text)
    except Exception as e:
        return {"error": str(e)}


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
        f"- {e['exercise_name']}: {e['prescribed_sets']}x{e['prescribed_reps']}"
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

    Sesión original prescrita:
    {ejercicios_texto}

    DEBES responder ÚNICAMENTE con un objeto JSON válido que siga exactamente esta estructura,
    sin texto adicional ni formato markdown:
    {{
        "session_focus": "string",
        "athlete_notes": "string (menciona que es una versión adaptada a {available_minutes} minutos)",
        "exercises": [
            {{
                "exercise_name": "string",
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
        return {"error": str(e)}
