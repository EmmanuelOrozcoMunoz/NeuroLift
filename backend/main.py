from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID
from datetime import timedelta
from sqlalchemy.orm import joinedload
from pydantic import BaseModel
import json
from passlib.context import CryptContext

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

            # 4. Parseo y guardado en Base de Datos (Ajustado a la estructura de Gemini)
            semanas = rutina_ai.get("weeks", [])
            
            for semana in semanas:
                sesiones = semana.get("sessions", [])
                
                for sesion_data in sesiones:
                    # Calculamos el día de la sesión
                    fecha_sesion = meso.start_date + timedelta(days=dias_agregados)
                    dias_agregados += 2 # Espaciamos 2 días (luego puedes mejorar esta lógica)

                    # 4.1 Crear la Sesión
                    nueva_sesion = models.Session(
                        mesocycle_id=meso.id,
                        scheduled_date=fecha_sesion,
                        athlete_notes=sesion_data.get("athlete_notes", ""),
                        status="pending"
                    )
                    db.add(nueva_sesion)
                    db.flush() 

                    contador_orden = 1
                    ejercicios = sesion_data.get("exercises", [])
                    
                    # 4.2 Iterar sobre los ejercicios
                    for ej_data in ejercicios:
                        nombre_ejercicio = ej_data.get("exercise_name", "Ejercicio Desconocido")
                        
                        # Buscar o crear el ejercicio en la BD
                        ejercicio = db.query(models.Exercise).filter(models.Exercise.name == nombre_ejercicio).first()
                        if not ejercicio:
                            ejercicio = models.Exercise(name=nombre_ejercicio, category="General")
                            db.add(ejercicio)
                            db.flush() 
                        
                        # 4.3 ¡Crear LAS series!
                        num_series = ej_data.get("prescribed_sets", 1)
                        reps = ej_data.get("prescribed_reps", 1)
                        
                        # --- BLINDAJE RPE ---
                        rpe_raw = ej_data.get("rpe_target") or ej_data.get("rpe")
                        rpe_limpio = int(float(rpe_raw)) if rpe_raw is not None else None

                        # --- BLINDAJE Y EXTRACCIÓN DE PESO ---
                        peso_raw = (
                            ej_data.get("prescribed_weight")
                            or ej_data.get("weight_kg")
                            or ej_data.get("weight")
                            or ej_data.get("target_weight")
                        )
                        peso_limpio = None
                        if peso_raw is not None:
                            try:
                                peso_limpio = float(peso_raw)
                            except (ValueError, TypeError):
                                peso_limpio = None
                        # -------------------------------------
                        
                        for _ in range(num_series):
                            nuevo_set = models.Set(
                                session_id=nueva_sesion.id,
                                exercise_id=ejercicio.id,
                                set_order=contador_orden,
                                prescribed_reps=reps,
                                rpe=rpe_limpio,
                                prescribed_weight=peso_limpio # Usamos el peso limpio
                            )
                            db.add(nuevo_set)
                            contador_orden += 1

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
        
    # ==========================================
    # BLINDAJE DE ORDENAMIENTO (SORTING)
    # ==========================================
    # 1. Ordenamos las sesiones por fecha de menor a mayor
    meso.sessions.sort(key=lambda s: s.scheduled_date)
    
    # 2. Entramos a cada sesión y ordenamos las series por su set_order (1, 2, 3...)
    for sesion in meso.sessions:
        sesion.sets.sort(key=lambda serie: serie.set_order)
    # ==========================================
        
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

# 1. Modificar serie existente
@app.put("/sets/{set_id}", response_model=schemas.SetResponse)
def update_set(set_id: UUID, set_update: schemas.SetUpdate, db: Session = Depends(get_db)):
    # 1. Buscamos la serie en la base de datos
    db_set = db.query(models.Set).filter(models.Set.id == set_id).first()
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie (Set) no encontrada")
    
    # 2. Actualizamos los datos numéricos (¡AQUÍ ESTÁ EL PESO!)
    db_set.prescribed_reps = set_update.prescribed_reps
    db_set.rpe = set_update.rpe
    db_set.prescribed_weight = set_update.prescribed_weight
    
    # 3. Lógica para el Pivote (Si el coach cambió el nombre del ejercicio)
    if set_update.exercise_name:
        # Buscamos si el nuevo ejercicio ya existe
        ejercicio = db.query(models.Exercise).filter(models.Exercise.name == set_update.exercise_name).first()
        if not ejercicio:
            # Si no existe, lo creamos
            ejercicio = models.Exercise(name=set_update.exercise_name, category="General")
            db.add(ejercicio)
            db.flush() # Guardamos rápido para obtener el ID
        
        # Le asignamos el nuevo ejercicio a la serie
        db_set.exercise_id = ejercicio.id

    # 4. Guardamos todo definitivamente
    db.commit()
    db.refresh(db_set)
    return db_set

# 2. NUEVO: Agregar una serie extra a la sesión
@app.post("/sessions/{session_id}/sets/")
def agregar_serie(session_id: UUID, req: schemas.SetCreate, db: Session = Depends(get_db)):
    sesion = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Buscamos o creamos el ejercicio nuevo
    ejercicio = db.query(models.Exercise).filter(models.Exercise.name == req.exercise_name).first()
    if not ejercicio:
        ejercicio = models.Exercise(name=req.exercise_name, category="Custom")
        db.add(ejercicio)
        db.flush()

    # Calculamos el orden (para que quede al final de la lista)
    series_actuales = db.query(models.Set).filter(models.Set.session_id == session_id).all()
    siguiente_orden = len(series_actuales) + 1

    nuevo_set = models.Set(
        session_id=session_id,
        exercise_id=ejercicio.id,
        set_order=siguiente_orden,
        prescribed_reps=req.prescribed_reps,
        rpe=req.rpe,
        prescribed_weight=req.prescribed_weight
    )
    db.add(nuevo_set)
    db.commit()
    return {"message": "Nueva serie agregada al final de la sesión"}

@app.delete("/sets/{set_id}")
def delete_set(set_id: UUID, db: Session = Depends(get_db)):
    db_set = db.query(models.Set).filter(models.Set.id == set_id).first()
    if not db_set:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    
    db.delete(db_set)
    db.commit()
    return {"message": "Serie eliminada correctamente"}

# Configuramos el encriptador de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# ==========================================
# ENDPOINTS DE AUTENTICACIÓN
# ==========================================
@app.post("/auth/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserRegister, db: Session = Depends(get_db)):
    # Verificamos si el email ya existe
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    nuevo_usuario = models.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password),
        role=user.role
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.post("/auth/login")
def login_user(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    usuario = db.query(models.User).filter(models.User.email == credentials.email).first()
    
    # Si no existe o la contraseña es incorrecta
    if not usuario or not verify_password(credentials.password, usuario.hashed_password):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    
    # Si todo está bien, le devolvemos los datos principales
    return {
        "id": str(usuario.id),
        "full_name": usuario.full_name,
        "email": usuario.email,
        "role": usuario.role
    }