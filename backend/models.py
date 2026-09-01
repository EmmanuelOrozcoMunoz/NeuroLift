import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    body_weight = Column(Float, nullable=True) # <-- El nuevo campo
    
    # Relaciones
    mesocycles = relationship("Mesocycle", back_populates="user")
    personal_records = relationship("PersonalRecord", back_populates="user", cascade="all, delete-orphan")

class Mesocycle(Base):
    __tablename__ = "mesocycles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    discipline = Column(String(50))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)
    ai_prompt_context = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="mesocycles")
    sessions = relationship("Session", back_populates="mesocycle", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mesocycle_id = Column(UUID(as_uuid=True), ForeignKey("mesocycles.id", ondelete="CASCADE"))
    scheduled_date = Column(Date, nullable=False)
    completed_date = Column(DateTime)
    status = Column(String(20), default="pending")
    athlete_notes = Column(Text)
    ai_feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

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
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    exercise_id = Column(UUID(as_uuid=True), ForeignKey("exercises.id"))
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

    session = relationship("Session", back_populates="sets")
    exercise = relationship("Exercise")



class PersonalRecord(Base):
    __tablename__ = "personal_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    exercise_name = Column(String, index=True) # Ej: "Back Squat", "Snatch"
    max_weight_kg = Column(Float)              # El 1RM en kilos
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="personal_records")