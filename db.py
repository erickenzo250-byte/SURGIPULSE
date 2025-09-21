from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, create_engine, Session

DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, echo=True)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str
    role: str = Field(default="staff")  # "admin" or "staff"

    surgeries: list["Surgery"] = Relationship(back_populates="staff")
    targets: list["Target"] = Relationship(back_populates="staff")


class Surgery(SQLModel, table=True):
    __tablename__ = "surgeries"

    id: int | None = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="users.id")
    surgery_type: str                 # trauma, spine, tumor, arthroplasty
    patient_id: str | None = None
    date: datetime = Field(default_factory=datetime.utcnow)
    duration_minutes: int | None = None
    outcome: str | None = None

    staff: User = Relationship(back_populates="surgeries")


class Target(SQLModel, table=True):
    __tablename__ = "targets"

    id: int | None = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="users.id")
    case_type: str = Field(default="all")  # trauma, spine, tumor, arthroplasty, or all
    target_cases: int
    period: str   # e.g. "2025-09"

    staff: User = Relationship(back_populates="targets")
    deliverables: list["Deliverable"] = Relationship(back_populates="target")


class Deliverable(SQLModel, table=True):
    __tablename__ = "deliverables"

    id: int | None = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="targets.id")
    deliverable_type: str = Field(default="cases")  # only "cases" for now
    is_completed: bool = Field(default=False)

    target: Target = Relationship(back_populates="deliverables")


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    return Session(engine)
