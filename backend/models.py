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
    body_weight = Column(Float, nullable=True)
    sex = Column(String(10), nullable=True)   # "male" | "female" — usado para el Fit Level
    age = Column(Integer, nullable=True)      # autorreportada, igual que body_weight
    # Se incrementa al cerrar sesión (o si un admin fuerza la revocación). Va embebido en cada
    # JWT emitido ("tv"); si no coincide con este valor, el token se rechaza aunque no haya
    # expirado todavía. Así se logra revocación real sin necesitar una tabla de blacklist.
    token_version = Column(Integer, nullable=False, default=0, server_default="0")


    # Relaciones
    # foreign_keys explícito: Mesocycle tiene DOS FKs a users (user_id = dueño del mesociclo,
    # created_by_coach_id = autor de la plantilla/plan), así que SQLAlchemy no puede adivinar.
    mesocycles = relationship("Mesocycle", back_populates="user", foreign_keys="Mesocycle.user_id")
    personal_records = relationship("PersonalRecord", back_populates="user", cascade="all, delete-orphan")
    coached_groups = relationship("Group", back_populates="coach", foreign_keys="Group.coach_id", cascade="all, delete-orphan")


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

    coach = relationship("User", back_populates="coached_groups", foreign_keys=[coach_id])
    members = relationship("User", secondary=group_members)

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

    user = relationship("User", back_populates="mesocycles", foreign_keys=[user_id])
    created_by_coach = relationship("User", foreign_keys=[created_by_coach_id])
    group = relationship("Group")
    sessions = relationship("Session", back_populates="mesocycle", cascade="all, delete-orphan")

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

    mesocycle = relationship("Mesocycle", back_populates="sessions")
    sets = relationship("Set", back_populates="session", cascade="all, delete-orphan")

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