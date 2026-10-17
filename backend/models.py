"""SQLModel tables: User, Project, Order (see plan.md section 6)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """All timestamps are stored in UTC."""
    return datetime.now(UTC)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    password_hash: str
    created_at: datetime = Field(default_factory=utcnow)


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    seller_id: int = Field(foreign_key="user.id", index=True)

    # Listing fields. A1 (autofill) fills these; the seller always edits them.
    title: str = ""
    tagline: str = ""
    description: str = ""
    tech_stack: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    category: str = ""
    difficulty: str = ""
    what_you_get: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    demo_points: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    price_inr: int = 0
    demo_url: str = ""

    # Source text and the uploaded ZIP (Day 2).
    readme_text: str = ""
    file_path: str | None = None

    status: str = "draft"  # draft | published
    ai_score: int | None = None
    ai_review: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    buyer_id: int = Field(foreign_key="user.id", index=True)
    amount_inr: int = 0
    provider: str = "mock"
    provider_ref: str | None = None
    status: str = "pending"  # pending | paid | failed
    created_at: datetime = Field(default_factory=utcnow)
