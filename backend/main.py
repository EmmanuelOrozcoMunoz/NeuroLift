from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID

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
        bodyweight=user.bodyweight
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
        end_date=mesocycle.end_date,
        ai_prompt_context=mesocycle.ai_prompt_context
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