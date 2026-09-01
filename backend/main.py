from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID
from datetime import timedelta
from sqlalchemy.orm import joinedload
from pydantic import BaseModel
import json

from backend.database import SessionLocal, engine
from backend import models, schemas

# Esto crea las tablas si por alguna razón no existieran en la BD
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NeuroLift API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def test_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "success", "message": "¡NeuroLift conectado a Supabase exitosamente!"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# --- NUEVOS ENDPOINTS PARA USUARIOS ---

@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Verificamos si el correo ya existe
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Creamos el nuevo usuario
    new_user = models.User(
        email=user.email,
        full_name=user.full_name,
        body_weight=user.body_weight
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/", response_model=List[schemas.UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return users

# --- ENDPOINTS PARA MESOCICLOS ---

@app.post("/mesocycles/", response_model=schemas.MesocycleResponse)
def create_mesocycle(mesocycle: schemas.MesocycleCreate, db: Session = Depends(get_db)):
    # Validamos que el usuario exista
    db_user = db.query(models.User).filter(models.User.id == mesocycle.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Creamos el mesociclo
    new_meso = models.Mesocycle(
        user_id=mesocycle.user_id,
        name=mesocycle.name,
        discipline=mesocycle.discipline,
        start_date=mesocycle.start_date,
    )
    db.add(new_meso)
    db.commit()
    db.refresh(new_meso)
    return new_meso

# --- ENDPOINTS PARA SESIONES ---

@app.post("/sessions/", response_model=schemas.SessionResponse)
def create_session(session: schemas.SessionCreate, db: Session = Depends(get_db)):
    # Validamos que el mesociclo exista
    db_meso = db.query(models.Mesocycle).filter(models.Mesocycle.id == session.mesocycle_id).first()
    if not db_meso:
        raise HTTPException(status_code=404, detail="Mesociclo no encontrado")
    
    new_session = models.Session(
        mesocycle_id=session.mesocycle_id,
        scheduled_date=session.scheduled_date
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

from pydantic import BaseModel
from datetime import date

# Esquema para recibir la petición de la IA
class AIGenerateRequest(BaseModel):
    mesocycle_id: UUID
    context: str
    weeks_count: int = 4
    sessions_per_week: int = 4

@app.post("/ai/generate-session/")
def generate_and_save_session(req: AIGenerateRequest, db: Session = Depends(get_db)):
    # 1. Buscamos el mesociclo y al atleta para darle el contexto real a la IA
    meso = db.query(models.Mesocycle).filter(models.Mesocycle.id == req.mesocycle_id).first()
    if not meso:
        raise HTTPException(status_code=404, detail="Mesociclo no encontrado")
    
    # 2. Llamamos a nuestro cerebro de IA
    from backend.ai_agent import generate_workout_session
    rutina_ai = generate_workout_session(
        athlete_name=meso.user.full_name, 
        discipline=meso.discipline, 
        experience_notes=req.context
    )
    
    if "error" in rutina_ai:
        raise HTTPException(status_code=500, detail=rutina_ai["error"])
        
    # 3. Guardamos la Sesión en la base de datos
    nueva_sesion = models.Session(
        mesocycle_id=meso.id,
        scheduled_date=date.today(),
        athlete_notes=rutina_ai.get("athlete_notes", ""),
        status="pending"
    )
    db.add(nueva_sesion)
    db.flush() # Guarda temporalmente para generar el ID de la sesión
    
    # 4. Guardamos las series y ejercicios
    orden = 1
    for ex_data in rutina_ai.get("exercises", []):
        # Buscamos si el ejercicio ya existe, si no, lo creamos
        ejercicio = db.query(models.Exercise).filter(models.Exercise.name == ex_data["exercise_name"]).first()
        if not ejercicio:
            ejercicio = models.Exercise(name=ex_data["exercise_name"], category="AI Generated")
            db.add(ejercicio)
            db.flush()
            
        # Creamos el Set
        nuevo_set = models.Set(
            session_id=nueva_sesion.id,
            exercise_id=ejercicio.id,
            set_order=orden,
            prescribed_reps=ex_data["prescribed_reps"],
            rpe=ex_data["rpe_target"]
            # Nota: prescribed_sets requeriría un bucle adicional para crear un registro por cada serie, 
            # pero lo simplificamos aquí para la prueba.
        )
        db.add(nuevo_set)
        orden += 1
        
    db.commit() # Confirmamos todos los cambios en Supabase
    db.refresh(nueva_sesion)
    
    return {"status": "success", "session_focus": rutina_ai.get("session_focus"), "session_id": nueva_sesion.id}

@app.post("/ai/generate-full-mesocycle/")
def generate_and_save_full_mesocycle(req: schemas.AIGenerateRequest, db: Session = Depends(get_db)):
    # 1. Buscar el "cascarón" del mesociclo
    meso = db.query(models.Mesocycle).filter(models.Mesocycle.id == req.mesocycle_id).first()
    if not meso:
        raise HTTPException(status_code=404, detail="Mesociclo no encontrado")

    # ==========================================
    # 2. CONSTRUIR EL SÚPER CONTEXTO (PESO Y RMs)
    # ==========================================
    atleta = meso.user
    marcas = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == atleta.id).all()
    
    texto_marcas = "Sin marcas registradas."
    if marcas:
        # Formateamos las marcas así: "Back Squat: 140.0kg, Bench Press: 100.0kg"
        texto_marcas = ", ".join([f"{pr.exercise_name}: {pr.max_weight_kg}kg" for pr in marcas])
    
    peso_corporal = f"{atleta.body_weight}kg" if atleta.body_weight else "No registrado"
    
    # Unimos lo que escribió el coach en la app + la base de datos
    contexto_enriquecido = f"Peso corporal: {peso_corporal}. Marcas actuales (1RM): {texto_marcas}. Peticiones del Coach: {req.context}"
    # ==========================================

    dias_agregados = 0
    semanas_por_chunk = 2 # (O 4, dependiendo de cómo estés dividiendo las llamadas)

    try:
        # 3. Bucle de generación por "chunks" (semanas)
        for start in range(1, req.weeks_count + 1, semanas_por_chunk):
            end = min(start + semanas_por_chunk - 1, req.weeks_count)
            
            # Llamamos a Gemini (Asegúrate de tener importada tu función search_knowledge_base y generate_mesocycle_chunk)
            from backend.ai_agent import generate_mesocycle_chunk
            
            rutina_ai = generate_mesocycle_chunk(
                athlete_name=atleta.full_name,
                discipline=meso.discipline,
                experience_notes=contexto_enriquecido, # <- ¡Aquí pasamos los RMs y el peso!
                start_week=start,
                end_week=end,
                sessions_per_week=req.sessions_per_week
            )

            # 4. Parseo y guardado en Base de Datos
            for sesion_data in rutina_ai.get("sessions", []):
                # Calculamos el día exacto de la sesión
                fecha_sesion = meso.start_date + timedelta(days=dias_agregados)
                
                # Aquí puedes hacer una lógica más pro para repartir los días en la semana.
                # Por ahora, le sumamos 2 días entre cada sesión para separarlas.
                dias_agregados += 2 

                nueva_sesion = models.Session(
                    mesocycle_id=meso.id,
                    scheduled_date=fecha_sesion,
                    athlete_notes=sesion_data.get("athlete_notes", ""),
                    status="pending"
                )
                db.add(nueva_sesion)
                db.flush() # Hace un "pre-guardado" para darnos el ID de la sesión

                for set_data in sesion_data.get("sets", []):
                    # Buscamos o creamos el ejercicio
                    nombre_ejercicio = set_data["exercise"]["name"]
                    ejercicio = db.query(models.Exercise).filter(models.Exercise.name == nombre_ejercicio).first()
                    
                    if not ejercicio:
                        ejercicio = models.Exercise(
                            name=nombre_ejercicio, 
                            category=set_data["exercise"].get("category", "General")
                        )
                        db.add(ejercicio)
                        db.flush() # Pre-guardado para obtener el ID del ejercicio
                    
                    nuevo_set = models.Set(
                        session_id=nueva_sesion.id,
                        exercise_id=ejercicio.id,
                        set_order=set_data.get("set_order", 1),
                        prescribed_reps=set_data.get("prescribed_reps", 1),
                        rpe=set_data.get("rpe")
                    )
                    db.add(nuevo_set)

        # 5. ACTUALIZAR LA FECHA DE FIN DEL MESOCICLO
        meso.end_date = meso.start_date + timedelta(days=dias_agregados)
        
        # 6. Ejecutar todo de golpe
        db.commit()
        return {"message": "Mesociclo generado y guardado exitosamente con cálculo de RMs."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno generando la rutina: {str(e)}")

@app.get("/mesocycles/{mesocycle_id}", response_model=schemas.MesocycleFullResponse)
def get_full_mesocycle(mesocycle_id: UUID, db: Session = Depends(get_db)):
    """
    Obtiene un mesociclo completo con todas sus sesiones, series y ejercicios anidados.
    """
    meso = db.query(models.Mesocycle).options(
        joinedload(models.Mesocycle.sessions)
        .joinedload(models.Session.sets)
        .joinedload(models.Set.exercise)
    ).filter(models.Mesocycle.id == mesocycle_id).first()
    
    if not meso:
        raise HTTPException(status_code=404, detail="Mesociclo no encontrado")
        
    return meso


@app.get("/mesocycles/", response_model=List[schemas.MesocycleResponse])
def listar_mesociclos(db: Session = Depends(get_db)):
    """Devuelve la lista de todos los mesociclos básicos."""
    return db.query(models.Mesocycle).all()

# Crear un nuevo atleta
@app.post("/users/", response_model=schemas.UserResponse)
def crear_atleta(user: schemas.UserCreate, db: Session = Depends(get_db)):
    nuevo_usuario = models.User(full_name=user.full_name, email=user.email)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

# Listar todos los atletas (para el menú desplegable del frontend)
@app.get("/users/", response_model=List[schemas.UserResponse])
def listar_atletas(db: Session = Depends(get_db)):
    return db.query(models.User).all()

# Esquema rápido para recibir la marca
class PRCreate(BaseModel):
    exercise_name: str
    max_weight_kg: float

@app.post("/users/{user_id}/records/")
def upsert_personal_record(user_id: UUID, record: PRCreate, db: Session = Depends(get_db)):
    """Añade una nueva marca o la actualiza si el ejercicio ya existe."""
    # Buscamos si el usuario ya tiene un RM registrado para este ejercicio
    pr_existente = db.query(models.PersonalRecord).filter(
        models.PersonalRecord.user_id == user_id,
        models.PersonalRecord.exercise_name == record.exercise_name
    ).first()

    if pr_existente:
        pr_existente.max_weight_kg = record.max_weight_kg
        db.commit()
        db.refresh(pr_existente)
        return {"message": f"RM de {record.exercise_name} actualizado a {record.max_weight_kg}kg"}
    else:
        nuevo_pr = models.PersonalRecord(
            user_id=user_id,
            exercise_name=record.exercise_name,
            max_weight_kg=record.max_weight_kg
        )
        db.add(nuevo_pr)
        db.commit()
        return {"message": f"Nuevo RM de {record.exercise_name} registrado."}

@app.get("/users/{user_id}/records/", response_model=List[schemas.PRResponse])
def obtener_marcas_atleta(user_id: UUID, db: Session = Depends(get_db)):
    """Devuelve todo el historial de marcas de un atleta."""
    marcas = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == user_id).all()
    return marcas

from pydantic import BaseModel

# Esquema para recibir las correcciones del Coach
class SetUpdate(BaseModel):
    prescribed_reps: int
    rpe: float | None = None

# Endpoint 1: Buscar mesociclos de un atleta específico
@app.get("/users/{user_id}/mesocycles/")
def obtener_mesociclos_usuario(user_id: UUID, db: Session = Depends(get_db)):
    mesociclos = db.query(models.Mesocycle).filter(models.Mesocycle.user_id == user_id).all()
    return mesociclos

# Endpoint 2: Actualizar una serie específica (Reps o RPE)
@app.put("/sets/{set_id}")
def actualizar_serie(set_id: UUID, req: SetUpdate, db: Session = Depends(get_db)):
    db_set = db.query(models.Set).filter(models.Set.id == set_id).first()
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    
    # Aplicamos los cambios del Coach
    db_set.prescribed_reps = req.prescribed_reps
    db_set.rpe = req.rpe
    db.commit()
    return {"message": "Serie actualizada correctamente"}