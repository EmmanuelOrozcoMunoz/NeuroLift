import os
import requests
import json
from dotenv import load_dotenv
from sqlalchemy import text
from backend.database import SessionLocal # Importamos tu conexión a la BD

load_dotenv()

def generate_workout_session(athlete_name: str, discipline: str, experience_notes: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY").strip() 
    
    # Manteniendo tu versión ganadora 3.6
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    
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
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        # Esto obliga a la API a devolver un JSON estricto
        "generationConfig": {
            "responseMimeType": "application/json",
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status() 
        data = response.json()
        
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
        res = requests.post(embed_url, json=payload)
        res.raise_for_status()
        vector_busqueda = res.json()["embedding"]["values"]
        
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
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status() 
        raw_json_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        
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
    api_key = os.getenv("GEMINI_API_KEY").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"

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

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        raw_json_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(raw_json_text)
    except Exception as e:
        return {"error": str(e)}