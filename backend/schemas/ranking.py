from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RankingLift(BaseModel):
    """Un levantamiento con marcas en el ranking del box."""
    key: str
    name: str
    athletes_count: int


class RankingLiftRow(BaseModel):
    rank: int
    user_id: UUID
    full_name: str
    has_avatar: bool = False
    weight_kg: float
    # "rx" | "scaled" | null: con qué categoría compite
    category: Optional[str] = None
    is_me: bool = False


class RankingWod(BaseModel):
    """Un WOD que atletas del box anotaron con resultado, agrupado por nombre y formato."""
    key: str
    name: str
    wod_format: str
    athletes_count: int
    last_date: date


class RankingWodRow(BaseModel):
    rank: int
    user_id: UUID
    full_name: str
    has_avatar: bool = False
    score_label: Optional[str] = None
    date: date
    category: Optional[str] = None
    is_me: bool = False
