import os
import requests
import PyPDF2
from dotenv import load_dotenv
from sqlalchemy import text

# Importamos tu conexión a la base de datos que ya tienes configurada
from backend.database import SessionLocal

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY").strip()
# URL para el modelo de embeddings
EMBEDDING_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={API_KEY}"

def get_embedding(text_chunk: str) -> list:
    """Llama a Google Gemini para convertir un fragmento de texto en un vector matemático de 768 dimensiones."""
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {
            "parts": [{"text": text_chunk}]
        }
    }
    response = requests.post(EMBEDDING_URL, json=payload)
    response.raise_for_status()
    # Extraemos la lista de números del JSON que devuelve Google
    return response.json()["embedding"]["values"]

def process_and_upload_pdf(pdf_path: str, source_name: str):
    print(f"📚 Abriendo '{source_name}'...")
    
    # 1. Extraer todo el texto del PDF
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            full_text = ""
            for page in reader.pages:
                text_page = page.extract_text()
                if text_page:
                    full_text += text_page + "\n"
    except Exception as e:
        print(f"❌ Error leyendo el PDF: {e}")
        return
                    
    # 2. Picar el texto en "chunks" (fragmentos)
    # Lo partimos en pedazos de 1000 caracteres para que la IA no pierda el contexto
    chunk_size = 1000
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    print(f"✂️ PDF dividido en {len(chunks)} fragmentos. Iniciando conversión a vectores...")

    # 3. Convertir y guardar en Supabase
    db = SessionLocal()
    try:
        for i, chunk in enumerate(chunks):
            # Limpiamos el texto y saltamos fragmentos vacíos o basura
            clean_chunk = chunk.strip()
            if len(clean_chunk) < 50:
                continue 
            
            print(f"🧠 Procesando fragmento {i+1}/{len(chunks)}...")
            vector = get_embedding(clean_chunk)
            
            # Guardamos usando SQL crudo para inyectar directo a la tabla de pgvector
            query = text("""
                INSERT INTO knowledge_base (source_name, content, embedding)
                VALUES (:source, :content, :embedding)
            """)
            db.execute(query, {
                "source": source_name,
                "content": clean_chunk,
                # pgvector en SQL lee los vectores como un string de lista '[0.1, 0.2, ...]'
                "embedding": str(vector) 
            })
        
        db.commit()
        print("✅ ¡Inyección de conocimiento completada con éxito! La IA ahora es más inteligente.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error al subir a la Base de Datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # 1. Obtenemos la ruta exacta de la carpeta donde está guardado este script
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Escribe el nombre exacto de tu PDF aquí
    nombre_pdf = "bases_levantamiento_olimpico_15_paginas.pdf"  # Cambia esto al nombre de tu PDF
    
    # 3. Construimos la ruta blindada
    archivo_pdf = os.path.join(directorio_actual, nombre_pdf)
    
    if os.path.exists(archivo_pdf):
        # Le pasamos nombre_pdf como "source" para que en la base de datos se vea limpio
        process_and_upload_pdf(archivo_pdf, nombre_pdf)
    else:
        print(f"⚠️ No se encontró el archivo '{nombre_pdf}'.")
        print(f"👉 Asegúrate de que esté guardado en: {directorio_actual}")