import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Date, ForeignKey, Text, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False) # Contraseña (bcrypt), siempre generada por la app
    role = Column(String, default="athlete")
    created_at = Column(DateTime, default=datetime.utcnow)
    body_weight = Column(Float, nullable=True)
    sex = Column(String(10), nullable=True)   # "male" | "female" — usado para el Fit Level
    age = Column(Integer, nullable=True)      # autorreportada, igual que body_weight
    # "rx" | "scaled" — con qué categoría compite este atleta en los WODs. Junto con `sex`,
    # resuelve cuál de los 4 pesos (Rx H/M, Scaled H/M) que el coach prescribe para todo el
    # grupo le corresponde a este atleta en particular (ver backend/routers/groups.py).
    category = Column(String(10), nullable=True)
    # "kg" | "lb" — unidad en la que ESTE usuario prefiere escribir y leer cualquier peso en la
    # app (sus propias series, sus PRs, o -si es coach- lo que prescribe). null se trata como
    # "kg". El valor que se GUARDA siempre es en kg (los % de 1RM y el redondeo a 2.5kg no
    # cambian); esto solo afecta cómo se muestra/captura en el frontend.
    weight_unit = Column(String(10), nullable=True)
    # Si el box de este atleta tiene discos de 25kg — algunos boxes solo tienen de 20kg para
    # abajo. null se trata como True (sí tiene), para no romper la calculadora de discos de
    # quien no haya tocado esta preferencia. Afecta solo esa calculadora, nada del cálculo de
    # cargas prescritas (% de 1RM, redondeo a 2.5kg, etc.).
    has_25kg_plates = Column(Boolean, nullable=True)
    # Se incrementa al cerrar sesión (o si un admin fuerza la revocación). Va embebido en cada
    # JWT emitido ("tv"); si no coincide con este valor, el token se rechaza aunque no haya
    # expirado todavía. Así se logra revocación real sin necesitar una tabla de blacklist.
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
    # Nombre de archivo ALEATORIO (uuid4 + extensión detectada por magic number, nunca el
    # nombre que subió el usuario) de la foto de perfil ya re-renderizada y sin metadatos.
    # Vive en backend/uploads/avatars/ (fuera de cualquier raíz servida como estática) — ver
    # AVATAR_DIR en main.py. None = sin foto de perfil.
    avatar_filename = Column(String(255), nullable=True)
    # Coach "dueño" directo de este atleta (solo tiene sentido cuando role="athlete"): se fija
    # automáticamente cuando un coach autenticado crea la cuenta desde /auth/register (ver
    # main.py). Si el atleta se auto-registró por su cuenta, queda en None ("sin afiliar") hasta
    # que un coach lo agregue a un grupo (eso también le da acceso, vía Group.members) o lo
    # reclame explícitamente. Es la base de que "cada coach solo vea a sus propios atletas".
    coach_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    @property
    def has_avatar(self) -> bool:
        return self.avatar_filename is not None

    # Relaciones
    # foreign_keys explícito: Mesocycle tiene DOS FKs a users (user_id = dueño del mesociclo,
    # created_by_coach_id = autor de la plantilla/plan), así que SQLAlchemy no puede adivinar.
    mesocycles = relationship("Mesocycle", back_populates="user", foreign_keys="Mesocycle.user_id")
    personal_records = relationship("PersonalRecord", back_populates="user", cascade="all, delete-orphan")
    coached_groups = relationship("Group", back_populates="coach", foreign_keys="Group.coach_id", cascade="all, delete-orphan")
    coach = relationship("User", remote_side=[id], foreign_keys=[coach_id])


# Tabla puente para la relación muchos-a-muchos Grupo <-> Atleta
group_members = Table(
    "group_members",
    Base.metadata,
    Column("group_id", UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class Group(Base):
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coach_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Foto de portada (mismo pipeline de saneo que el avatar de usuario: magic-number, re-render
    # sin metadatos, nombre aleatorio). Vive en backend/uploads/group_covers/. None = sin foto.
    cover_image_filename = Column(String(255), nullable=True)

    coach = relationship("User", back_populates="coached_groups", foreign_keys=[coach_id])
    members = relationship("User", secondary=group_members)

    @property
    def has_cover_image(self) -> bool:
        return self.cover_image_filename is not None

class Mesocycle(Base):
    __tablename__ = "mesocycles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    discipline = Column(String(50))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)
    ai_prompt_context = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # --- PLANES (plantillas vendibles, sin dueño) ---
    # Un "plan" es un Mesocycle con is_template=True y user_id=None: no pertenece a ningún
    # atleta, sirve de plantilla que cualquiera puede adquirir. Al adquirirlo se clona en un
    # mesociclo normal (is_template=False, user_id=comprador) con fechas y pesos reales.
    is_template = Column(Boolean, default=False, nullable=False, server_default="false")
    is_published = Column(Boolean, default=False, nullable=False, server_default="false")
    created_by_coach_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(Text)
    level = Column(String(20))          # "Principiante" | "Intermedio" | "Avanzado"
    price = Column(Float, nullable=True)
    source_plan_id = Column(UUID(as_uuid=True), ForeignKey("mesocycles.id", ondelete="SET NULL"), nullable=True)
    # Foto de portada del plan (mismo pipeline de saneo que el avatar de usuario). Solo tiene
    # sentido en plantillas (is_template=True) pero vive en esta tabla como el resto de campos
    # exclusivos de plan (description, level, price). Vive en backend/uploads/plan_covers/.
    cover_image_filename = Column(String(255), nullable=True)

    user = relationship("User", back_populates="mesocycles", foreign_keys=[user_id])
    created_by_coach = relationship("User", foreign_keys=[created_by_coach_id])
    group = relationship("Group")
    # passive_deletes=True: al borrar un mesociclo/plan, deja que la base de datos borre las
    # sesiones en cascada ella misma (ya tiene ON DELETE CASCADE) en vez de que SQLAlchemy traiga
    # cada sesión a memoria y la borre una por una — con Supabase (remoto, no localhost), un plan
    # con varias semanas podía significar cientos de idas y vueltas de red para un solo borrado.
    # passive_deletes=True: al borrar un mesociclo/plan, deja que la base de datos borre las
    # sesiones en cascada ella misma (ya tiene ON DELETE CASCADE) en vez de que SQLAlchemy traiga
    # cada sesión a memoria y la borre una por una — con Supabase (remoto, no localhost), un plan
    # con varias semanas podía significar cientos de idas y vueltas de red para un solo borrado.
    sessions = relationship("Session", back_populates="mesocycle", cascade="all, delete-orphan", passive_deletes=True)

    @property
    def has_cover_image(self) -> bool:
        return self.cover_image_filename is not None

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mesocycle_id = Column(UUID(as_uuid=True), ForeignKey("mesocycles.id", ondelete="CASCADE"), index=True)
    scheduled_date = Column(Date, nullable=False)
    completed_date = Column(DateTime)
    status = Column(String(20), default="pending")
    athlete_notes = Column(Text)
    ai_feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Si no es null, esta sesión es una versión "adaptada al tiempo" de la sesión original
    # (mismo día, mismo mesociclo, pero un plan más corto). La original nunca se toca.
    parent_session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    duration_minutes = Column(Integer, nullable=True)  # duración objetivo de esta sesión, si se definió
    # Solo en sesiones de PLANES (plantillas): "día N" relativo al inicio del plan. La plantilla
    # también guarda un scheduled_date sintético (PLAN_EPOCH + day_offset) para no romper el
    # ordenamiento ni las vistas existentes; al adquirir el plan se recalcula la fecha real.
    day_offset = Column(Integer, nullable=True)
    # Orden de los bloques que el coach eligió para ESTA sesión, como texto separado por comas
    # (ej. "warmup,strength,metcon") — null usa el orden canónico de siempre (ver
    # web/src/lib/blocks.ts:BLOCK_KEYS). Cualquier bloque presente en la sesión pero ausente de
    # esta lista se agrega al final, en su posición canónica (ver groupByBlock en sessions.ts).
    block_order = Column(String(200), nullable=True)
    # Pautas de calentamiento/aproximaciones que el coach escribe para esta sesión — se muestran
    # al atleta ANTES del primer bloque de series. Distinto de athlete_notes (ese lo llena la IA
    # con el enfoque general de la sesión; este lo escribe el coach a mano para el calentamiento).
    warmup_notes = Column(Text, nullable=True)

    # --- RESULTADO DEL WOD/METCON (formatos estándar de CrossFit) ---
    # El coach prescribe el formato (y opcionalmente un time cap/duración) al programar la
    # sesión; el atleta reporta su resultado real al completarla (ver PUT /sessions/{id}/wod-format
    # y POST /sessions/{id}/complete). "for_time": tiempo total (wod_time_seconds), con time cap
    # opcional. "amrap": rondas completas + reps sueltas del intento final (wod_rounds/
    # wod_extra_reps). "amrap_reps": AMRAP puntuado solo en reps totales, sin rondas visibles
    # (wod_extra_reps). "emom"/"e2mom": si mantuvo el ritmo todo el tiempo (wod_emom_completed).
    # "1rm": no necesita campos propios — el peso máximo ya queda en Set.actual_weight de esa
    # sesión. "calories"/"distance"/"watts": total logrado en el tiempo prescrito.
    wod_format = Column(String(20), nullable=True)
    # Timer que fija el coach al prescribir: cap duro para "for_time", duración de la ventana
    # para amrap/amrap_reps/calories/distance/watts. No aplica a emom/1rm.
    wod_time_cap_seconds = Column(Integer, nullable=True)
    wod_time_seconds = Column(Integer, nullable=True)
    wod_rounds = Column(Integer, nullable=True)
    wod_extra_reps = Column(Integer, nullable=True)
    wod_emom_completed = Column(Boolean, nullable=True)
    wod_calories = Column(Float, nullable=True)
    wod_distance_meters = Column(Float, nullable=True)
    wod_watts = Column(Float, nullable=True)

    mesocycle = relationship("Mesocycle", back_populates="sessions")
    # Mismo motivo que Mesocycle.sessions: deja que la base de datos borre las series en cascada
    # (ya tiene ON DELETE CASCADE) en vez de traerlas todas a memoria para borrarlas una por una.
    # Mismo motivo que Mesocycle.sessions: deja que la base de datos borre las series en cascada
    # (ya tiene ON DELETE CASCADE) en vez de traerlas todas a memoria para borrarlas una por una.
    sets = relationship("Set", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)

class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))
    description = Column(Text)

class Set(Base):
    __tablename__ = "sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    exercise_id = Column(UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="SET NULL"), nullable=True)
    set_order = Column(Integer, nullable=False)
    # Parte de la sesión a la que pertenece este ejercicio (calentamiento, fuerza, weightlifting,
    # skills/gimnasia, metabólico...). Ver backend/schemas.py:Bloque para los valores válidos y
    # web/src/lib/blocks.ts para las etiquetas/orden en el frontend. None = sin bloque asignado
    # (series creadas antes de esta función, o el coach no lo especificó).
    block = Column(String(30), nullable=True)
    prescribed_reps = Column(Integer)
    prescribed_weight = Column(Float)
    actual_reps = Column(Integer)
    actual_weight = Column(Float)
    rpe = Column(Integer)
    video_url = Column(String(255))
    technique_score = Column(Float)
    technique_feedback = Column(Text)
    is_pr_attempt = Column(Boolean, default=False)
    # En los planes las cargas se prescriben en % de 1RM (el autor no conoce las marcas del
    # comprador). Al adquirir el plan se resuelve a kg usando el PR del atleta para
    # `reference_exercise` (o para el propio ejercicio si no se especifica otro).
    prescribed_percentage = Column(Float, nullable=True)
    reference_exercise = Column(String(100), nullable=True)

    session = relationship("Session", back_populates="sets")
    exercise = relationship("Exercise")



class PersonalRecord(Base):
    __tablename__ = "personal_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exercise_name = Column(String, index=True) # Ej: "Back Squat", "Snatch"
    max_weight_kg = Column(Float)              # El 1RM en kilos
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="personal_records")


class FitnessBenchmark(Base):
    """Una marca del calculador de 'Fit Level' (halterofilia/gimnasia/metcon). Diseño
    clave-valor: una fila por (atleta, métrica) — la unidad e interpretación de `value`
    la define `metric_key` en backend/fitness_scoring.py, no esta tabla."""
    __tablename__ = "fitness_benchmarks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    metric_key = Column(String(50), nullable=False)  # ej. "snatch_kg", "pull_ups_max", "fran_seconds"
    value = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", "metric_key", name="uq_fitness_benchmark_user_metric"),
    )


class AuditLog(Base):
    """Espejo persistente de lo que ya emite `security_logger` en main.py (logins fallidos,
    401/403, cambios de rol, revocaciones) — antes solo vivía en la consola del proceso y
    desaparecía al reiniciar. Un `logging.Handler` (ver main.py) escribe aquí en cada evento;
    esta tabla no reemplaza el logging a consola, lo complementa para que quede consultable
    desde el panel de admin."""
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)