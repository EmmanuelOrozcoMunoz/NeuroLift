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

def generate_mesocycle_chunk(athlete_name: str, discipline: str, experience_notes: str, start_week: int, end_week: int, sessions_per_week: int) -> dict:
    api_key = os.getenv("GEMINI_API_KEY").strip() 
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"

    # ¡AQUÍ ESTÁ LA MAGIA! Buscamos en el libro basándonos en lo que necesita el atleta
    literatura_cientifica = search_knowledge_base(f"{discipline} - {experience_notes}")
    
    prompt = f"""
    Eres el Head Coach de IA de NeuroLift. Estamos construyendo un mesociclo grande por partes.
    Genera SOLO desde la SEMANA {start_week} hasta la SEMANA {end_week} para este atleta.

    REGLA ESTRICTA: El atleta entrena EXACTAMENTE {sessions_per_week} días a la semana. 
    DEBES generar exactamente {sessions_per_week} objetos de sesión dentro del array 'sessions' por cada semana.

    Aplica sobrecarga progresiva en estas semanas específicas.

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
                        "day_name": "string",
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
        
        # Limpieza de seguridad por si Gemini añade formato markdown ```json
        raw_json_text = raw_json_text.replace("```json", "").replace("```", "").strip()
        
        import json
        return json.loads(raw_json_text)
    except Exception as e:
        return {"error": str(e)}