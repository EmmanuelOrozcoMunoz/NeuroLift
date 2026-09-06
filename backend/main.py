from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from uuid import UUID
from datetime import timedelta, datetime
from sqlalchemy.orm import joinedload
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
import jwt


from backend.database import SessionLocal, engine
from backend import models, schemas

# Esto crea las tablas si por alguna razón no existieran en la BD
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NeuroLift API")

# Le decimos a FastAPI dónde está la ruta de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

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

@app.post("/ai/generate-smart-mesocycle/")
def generate_and_save_smart_mesocycle(req: schemas.AIGenerateSmart, db: Session = Depends(get_db)):
    
    # 1. Crear el cascarón del mesociclo
    nuevo_meso = models.Mesocycle(
        user_id=req.user_id,
        name=req.name,
        discipline=req.discipline,
        start_date=req.start_date
    )
    db.add(nuevo_meso)
    db.flush() 

    # 2. CONSTRUIR EL SÚPER CONTEXTO (PESO Y RMs)
    atleta = db.query(models.User).filter(models.User.id == req.user_id).first()
    marcas = db.query(models.PersonalRecord).filter(models.PersonalRecord.user_id == atleta.id).all()
    
    texto_marcas = "Sin marcas registradas."
    if marcas:
        texto_marcas = ", ".join([f"{pr.exercise_name}: {pr.max_weight_kg}kg" for pr in marcas])
    
    peso_corporal = f"{atleta.body_weight}kg" if atleta.body_weight else "No registrado"
    contexto_enriquecido = f"Peso corporal: {peso_corporal}. Marcas (1RM): {texto_marcas}. Peticiones: {req.context}"

    # 3. CALCULAR TODAS LAS FECHAS DEL MESOCICLO
    total_dias = req.weeks_count * 7
    todas_las_fechas = []
    for i in range(total_dias):
        fecha_evaluada = req.start_date + timedelta(days=i)
        if fecha_evaluada.weekday() in req.training_days:
            todas_las_fechas.append(fecha_evaluada.strftime("%Y-%m-%d"))

    semanas_por_chunk = 2 
    sesiones_por_semana = len(req.training_days)
    sesiones_por_chunk = semanas_por_chunk * sesiones_por_semana

    try:
        # 4. Bucle de generación por "chunks" (semanas)
        from backend.ai_agent import generate_mesocycle_chunk
        
        for start in range(1, req.weeks_count + 1, semanas_por_chunk):
            end = min(start + semanas_por_chunk - 1, req.weeks_count)
            
            # Rebanamos la lista de fechas para enviarle solo las que tocan en este chunk
            idx_inicio = (start - 1) * sesiones_por_semana
            idx_fin = idx_inicio + sesiones_por_chunk
            fechas_del_chunk = todas_las_fechas[idx_inicio:idx_fin]
            
            rutina_ai = generate_mesocycle_chunk(
                athlete_name=atleta.full_name,
                discipline=req.discipline,
                experience_notes=contexto_enriquecido,
                start_week=start,
                end_week=end,
                session_dates=fechas_del_chunk # <- ¡Le pasamos las fechas exactas!
            )

            # 5. Parseo y guardado en Base de Datos
            semanas = rutina_ai.get("weeks", [])
            for semana in semanas:
                sesiones = semana.get("sessions", [])
                
                for sesion_data in sesiones:
                    # ¡LA MAGIA! Ahora Gemini nos devuelve la fecha exacta en el JSON
                    fecha_str = sesion_data.get("scheduled_date")
                    if fecha_str:
                        fecha_real = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    else:
                        fecha_real = req.start_date # Fallback por seguridad

                    # 5.1 Crear la Sesión
                    nueva_sesion = models.Session(
                        mesocycle_id=nuevo_meso.id,
                        scheduled_date=fecha_real,
                        athlete_notes=sesion_data.get("athlete_notes", ""),
                        status="pending"
                    )
                    db.add(nueva_sesion)
                    db.flush() 

                    contador_orden = 1
                    ejercicios = sesion_data.get("exercises", [])
                    
                    # 5.2 Iterar sobre los ejercicios (Igual que lo tenías)
                    for ej_data in ejercicios:
                        nombre_ejercicio = ej_data.get("exercise_name", "Ejercicio Desconocido")
                        ejercicio = db.query(models.Exercise).filter(models.Exercise.name == nombre_ejercicio).first()
                        if not ejercicio:
                            ejercicio = models.Exercise(name=nombre_ejercicio, category="General")
                            db.add(ejercicio)
                            db.flush() 
                        
                        num_series = ej_data.get("prescribed_sets", 1)
                        reps = ej_data.get("prescribed_reps", 1)
                        
                        rpe_raw = ej_data.get("rpe_target") or ej_data.get("rpe")
                        rpe_limpio = int(float(rpe_raw)) if rpe_raw is not None else None

                        peso_raw = (ej_data.get("prescribed_weight") or ej_data.get("weight_kg") or ej_data.get("weight") or ej_data.get("target_weight"))
                        peso_limpio = None
                        if peso_raw is not None:
                            try:
                                peso_limpio = float(peso_raw)
                            except (ValueError, TypeError):
                                peso_limpio = None
                        
                        for _ in range(num_series):
                            nuevo_set = models.Set(
                                session_id=nueva_sesion.id,
                                exercise_id=ejercicio.id,
                                set_order=contador_orden,
                                prescribed_reps=reps,
                                rpe=rpe_limpio,
                                prescribed_weight=peso_limpio 
                            )
                            db.add(nuevo_set)
                            contador_orden += 1

        # 6. ACTUALIZAR LA FECHA DE FIN
        nuevo_meso.end_date = datetime.strptime(todas_las_fechas[-1], "%Y-%m-%d").date()
        db.commit()
        return {"message": "Mesociclo Inteligente generado y guardado exitosamente."}

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


@app.post("/users/{user_id}/records/")
def upsert_personal_record(user_id: UUID, record: schemas.PRCreate, db: Session = Depends(get_db)):
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
    
    if not usuario or not verify_password(credentials.password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Correo o contraseña incorrectos"
        )
    
    # Fabricamos el contenido del token (Payload)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": usuario.email, "role": usuario.role, "id": str(usuario.id)},
        expires_delta=access_token_expires
    )
    
    # Devolvemos el Token en el formato estándar OAuth2
    return {"access_token": access_token, "token_type": "bearer"}
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Desencriptamos el token usando nuestra clave secreta
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError: # Atrapa tokens expirados o falsificados
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# El frontend llamará a esta ruta enviando el Token para hidratar la sesión
@app.get("/auth/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# 1. Ruta para que el Coach vea a sus atletas en un menú desplegable
@app.get("/users/athletes", response_model=List[schemas.UserResponse])
def get_athletes(db: Session = Depends(get_db)):
    # Traemos solo a los usuarios que tienen el rol de 'athlete'
    atletas = db.query(models.User).filter(models.User.role == "athlete").all()
    return atletas

# 2. Ruta para crear el Mesociclo Manual (Solo el cascarón y las sesiones vacías)
@app.post("/mesocycles/manual")
def create_manual_mesocycle(req: schemas.MesocycleManualCreate, db: Session = Depends(get_db)):
    # 1. Crear el cascarón principal
    nuevo_meso = models.Mesocycle(
        user_id=req.user_id,
        name=req.name,
        discipline=req.discipline,
        start_date=req.start_date
    )
    db.add(nuevo_meso)
    db.flush() # Guardamos para obtener el ID

    # 2. Lógica de Calendario Inteligente
    total_dias_mesociclo = req.weeks_count * 7
    sesiones_creadas = 0

    for i in range(total_dias_mesociclo):
        # Calculamos la fecha actual en el bucle
        fecha_evaluada = req.start_date + timedelta(days=i)
        
        # .weekday() devuelve 0 para Lunes, 1 para Martes, etc.
        if fecha_evaluada.weekday() in req.training_days:
            nueva_sesion = models.Session(
                mesocycle_id=nuevo_meso.id,
                scheduled_date=fecha_evaluada,
                athlete_notes="Sesión manual. Añade tus ejercicios.",
                status="pending"
            )
            db.add(nueva_sesion)
            sesiones_creadas += 1

    # 3. Actualizamos la fecha de fin real y guardamos definitivamente
    nuevo_meso.end_date = req.start_date + timedelta(days=total_dias_mesociclo - 1)
    db.commit()
    
    return {
        "message": "Mesociclo manual creado con éxito", 
        "mesocycle_id": str(nuevo_meso.id),
        "total_sessions": sesiones_creadas
    }
# ==========================================
# CONFIGURACIÓN JWT
# ==========================================
# En un proyecto real, esta clave va en un archivo .env
SECRET_KEY = "neurolift_super_secreto_no_compartir" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # El token durará 7 días


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt