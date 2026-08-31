import os
import requests
import json
from dotenv import load_dotenv

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