"""A1 autofill, A2 review and A3 ask. Output is schema-constrained and advisory."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

import auth
import schemas
from db import get_session
from models import Project, User
from services import llm
from services.prompts import (
    SYSTEM_ASK,
    SYSTEM_AUTOFILL,
    SYSTEM_REVIEW,
    ask_user,
    autofill_user,
    project_context,
    review_user,
)

router = APIRouter(prefix="/ai", tags=["ai"])

# A3 hangs off the project it answers about, even though the prompt lives here.
projects_router = APIRouter(prefix="/projects", tags=["ai"])


@router.post("/autofill", response_model=schemas.AutofillResult)
async def autofill(
    payload: schemas.AutofillRequest,
    user: User = Depends(auth.get_current_user),
) -> schemas.AutofillResult:
    """Turn a pasted README into listing fields. The seller still edits everything."""
    readme_text = llm.truncate(payload.readme_text)
    if not readme_text:
        raise HTTPException(status_code=400, detail="paste a README or project description first")

    try:
        return await llm.structured(
            schemas.AutofillResult,
            system=SYSTEM_AUTOFILL,
            user=autofill_user(readme_text),
            temperature=llm.TEMPERATURE_EXTRACT,
        )
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=f"autofill failed: {exc}") from exc


@router.post("/review", response_model=schemas.ReviewResult)
async def review(
    payload: schemas.ReviewRequest,
    user: User = Depends(auth.get_current_user),
    session: Session = Depends(get_session),
) -> schemas.ReviewResult:
    """Score a listing and list what is missing. Advisory: it never publishes anything."""
    if payload.project_id is not None:
        project = session.get(Project, payload.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        if project.seller_id != user.id:
            raise HTTPException(status_code=403, detail="you can only review your own projects")
        listing = schemas.ListingFields.model_validate(project, from_attributes=True)
        readme_text = payload.readme_text or project.readme_text
    else:
        listing = payload.listing
        readme_text = payload.readme_text

    try:
        result = await llm.structured(
            schemas.ReviewResult,
            system=SYSTEM_REVIEW,
            user=review_user(listing, llm.truncate(readme_text)),
            temperature=llm.TEMPERATURE_EXTRACT,
        )
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=f"review failed: {exc}") from exc

    if payload.project_id is not None:
        # Cache A2 on the project row so page views don't re-run the model.
        project.ai_score = result.score
        project.ai_review = result.model_dump()
        session.add(project)
        session.commit()
    return result


@projects_router.post("/{project_id}/ask", response_model=schemas.AskResult)
async def ask_project(
    project_id: int,
    payload: schemas.AskRequest,
    session: Session = Depends(get_session),
) -> schemas.AskResult:
    """A3: answer a buyer's question from this project's text only.

    No login: asking is part of browsing. The model gets one project's listing and
    README, has no tools, and says so when the answer is not in there.
    """
    project = session.get(Project, project_id)
    if project is None or project.status != "published":
        raise HTTPException(status_code=404, detail="project not found")

    listing = schemas.ListingFields.model_validate(project, from_attributes=True)
    context = project_context(listing, llm.truncate(project.readme_text))

    try:
        return await llm.structured(
            schemas.AskResult,
            system=SYSTEM_ASK,
            user=ask_user(payload.question.strip(), context),
            temperature=llm.TEMPERATURE_QA,
        )
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=f"could not answer that: {exc}") from exc
