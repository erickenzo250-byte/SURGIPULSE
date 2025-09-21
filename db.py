from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine, Session, Relationship
from typing import Optional, List

# -------------------------
# MODELS
# -------------------------

class Staff(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    role: str
    surgeries: List["Surgery"] = Relationship(back_populates="staff")
    targets: List["SurgeryTarget"] = Relationship(back_populates="staff")


class Surgery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    surgery_type: str
    date: datetime = Field(default_factory=datetime.utcnow)

    staff: Optional[Staff] = Relationship(back_populates="surgeries")


class SurgeryTarget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    month: str   # e.g. "2025-09"
    target_count: int
    achieved_count: int = 0

    staff: Optional[Staff] = Relationship(back_populates="targets")

# -------------------------
# DATABASE CONNECTION
# -------------------------

sqlite_url = "sqlite:///database.db"
engine = create_engine(sqlite_url, echo=True)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
