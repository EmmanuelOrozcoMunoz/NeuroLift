"""Búsqueda vectorial en la base de conocimiento (knowledge_base, pgvector) — la mitad "lectura"
de la tabla que backend/knowledge/cargar_pdf.py llena. Vivía dentro de ai_agent.py, pero no
tiene nada que ver con construir prompts de mesociclos/sesiones; solo comparte con ese módulo
la necesidad de llamar a la API de Gemini."""
import os

from sqlalchemy import text

from backend.ai_agent import _post_to_gemini
from backend.database import SessionLocal


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
