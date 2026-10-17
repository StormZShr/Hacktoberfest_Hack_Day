"""Request/response schemas plus the AI output schemas (A1-A3).

The AI schemas are also the JSON schemas handed to Ollama, so keep them small,
flat, and explicit: a small model does better with enums than with prose.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CATEGORIES = (
    "web-app",
    "mobile-app",
    "ml-ai",
    "cli-tool",
    "library",
    "game",
    "data",
    "other",
)
DIFFICULTIES = ("beginner", "intermediate", "advanced")


# --- Auth -------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: str
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    created_at: datetime


# --- Projects ---------------------------------------------------------------


class ListingFields(BaseModel):
    """The part of a project that A1 fills in. Seller-editable, so permissive."""

    model_config = ConfigDict(from_attributes=True)

    title: str = Field(default="", max_length=120)
    tagline: str = Field(default="", max_length=200)
    description: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    category: str = ""
    difficulty: str = ""
    what_you_get: list[str] = Field(default_factory=list)
    demo_points: list[str] = Field(default_factory=list)
    price_inr: int = Field(default=0, ge=0)
    demo_url: str = ""


class ProjectCreate(ListingFields):
    readme_text: str = ""


class ProjectUpdate(BaseModel):
    """Every field optional: a partial update of the seller's own draft."""

    title: str | None = Field(default=None, max_length=120)
    tagline: str | None = Field(default=None, max_length=200)
    description: str | None = None
    tech_stack: list[str] | None = None
    category: str | None = None
    difficulty: str | None = None
    what_you_get: list[str] | None = None
    demo_points: list[str] | None = None
    price_inr: int | None = Field(default=None, ge=0)
    demo_url: str | None = None
    readme_text: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    title: str
    tagline: str
    description: str
    tech_stack: list[str]
    category: str
    difficulty: str
    what_you_get: list[str]
    demo_points: list[str]
    price_inr: int
    demo_url: str
    status: str
    ai_score: int | None
    ai_review: dict[str, Any] | None
    has_file: bool = False
    created_at: datetime


class PublishResponse(BaseModel):
    id: int
    status: str


# --- AI: A1 autofill --------------------------------------------------------


class AutofillRequest(BaseModel):
    readme_text: str = Field(min_length=1)


class AutofillResult(BaseModel):
    title: str = Field(max_length=120)
    tagline: str = Field(max_length=200)
    description: str
    tech_stack: list[str]
    category: Literal[CATEGORIES]  # type: ignore[valid-type]
    difficulty: Literal[DIFFICULTIES]  # type: ignore[valid-type]
    what_you_get: list[str]
    demo_points: list[str]


# --- AI: A2 review ----------------------------------------------------------


class ReviewRequest(BaseModel):
    """Review a saved project, or review a listing that is not saved yet."""

    project_id: int | None = None
    listing: ListingFields | None = None
    readme_text: str = ""

    @model_validator(mode="after")
    def _need_a_listing(self) -> "ReviewRequest":
        if self.project_id is None and self.listing is None:
            raise ValueError("provide project_id or listing")
        return self


class ReviewResult(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str
    missing_items: list[str]
    risk_flags: list[str]
    suggestions: list[str]


# --- AI: A3 ask the project -------------------------------------------------


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AskResult(BaseModel):
    answer: str
    in_listing: bool


# --- Orders -----------------------------------------------------------------


class OrderCreate(BaseModel):
    project_id: int


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    project_title: str = ""
    amount_inr: int
    provider: str
    provider_ref: str | None
    status: str
    created_at: datetime
