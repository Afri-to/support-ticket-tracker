"""Database tables.

Agents and categories live in their own tables so a typo fix or rename is one
row, and KPI queries group by an id instead of repeated text.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)


class Import(Base):
    """One uploaded CSV file and what happened to its rows."""

    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    total_rows: Mapped[int] = mapped_column(Integer)
    imported: Mapped[int] = mapped_column(Integer)
    duplicates: Mapped[int] = mapped_column(Integer)
    already_imported: Mapped[int] = mapped_column(Integer)
    invalid: Mapped[int] = mapped_column(Integer)


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint("closed_at IS NULL OR closed_at >= opened_at", name="closed_after_opened"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(10), unique=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    root_cause: Mapped[str] = mapped_column(String(100))
    # values_callable stores "High" (what people read) instead of the name "HIGH".
    priority: Mapped[Priority] = mapped_column(
        SAEnum(Priority, name="priority", values_callable=lambda e: [m.value for m in e])
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    import_id: Mapped[int] = mapped_column(ForeignKey("imports.id"))

    agent: Mapped[Agent] = relationship()
    category: Mapped[Category] = relationship()
