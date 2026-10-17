"""Project endpoints: create, update, list, get, upload, publish, download.

Publish requirements, ownership and download gating are plain code here, never
the model's opinion.
"""

import re

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlmodel import Session, select

import auth
import schemas
from db import get_session
from models import Order, Project, User
from services import storage

router = APIRouter(prefix="/projects", tags=["projects"])


def to_read(project: Project) -> schemas.ProjectRead:
    return schemas.ProjectRead(
        **project.model_dump(exclude={"file_path", "readme_text"}),
        has_file=bool(project.file_path),
    )


def zip_filename(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return f"{slug or 'project'}.zip"


def get_owned_project(project_id: int, user: User, session: Session) -> Project:
    """Load a project and enforce ownership."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    if project.seller_id != user.id:
        raise HTTPException(status_code=403, detail="this project belongs to another seller")
    return project


@router.get("", response_model=list[schemas.ProjectRead])
def list_projects(
    q: str | None = Query(default=None, description="free-text match on title, tagline, description"),
    category: str | None = None,
    tech: str | None = None,
    max_price: int | None = Query(default=None, ge=0),
    session: Session = Depends(get_session),
) -> list[schemas.ProjectRead]:
    statement = select(Project).where(Project.status == "published")
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(Project.title).like(like),
                func.lower(Project.tagline).like(like),
                func.lower(Project.description).like(like),
            )
        )
    if category and category.strip():
        statement = statement.where(Project.category == category.strip())
    if tech and tech.strip():
        statement = statement.where(Project.tech_stack.like(f"%{tech.strip()}%"))
    if max_price is not None:
        statement = statement.where(Project.price_inr <= max_price)

    projects = session.exec(statement.order_by(Project.created_at.desc())).all()
    return [to_read(project) for project in projects]


@router.get("/mine", response_model=list[schemas.ProjectRead])
def my_projects(
    user: User = Depends(auth.get_current_user),
    session: Session = Depends(get_session),
) -> list[schemas.ProjectRead]:
    """The seller's own listings, drafts included."""
    statement = select(Project).where(Project.seller_id == user.id).order_by(Project.created_at.desc())
    return [to_read(project) for project in session.exec(statement).all()]


@router.get("/{project_id}", response_model=schemas.ProjectRead)
def get_project(
    project_id: int,
    user: User | None = Depends(auth.get_optional_user),
    session: Session = Depends(get_session),
) -> schemas.ProjectRead:
    project = session.get(Project, project_id)
    # Drafts stay private: anyone else gets the same 404 as a missing project.
    if project is None or (project.status != "published" and (user is None or user.id != project.seller_id)):
        raise HTTPException(status_code=404, detail="project not found")
    return to_read(project)


@router.post("", response_model=schemas.ProjectRead, status_code=201)
def create_project(
    payload: schemas.ProjectCreate,
    user: User = Depends(auth.get_current_user),
    session: Session = Depends(get_session),
) -> schemas.ProjectRead:
    project = Project(
        seller_id=user.id,
        status="draft",
        **payload.model_dump(),
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return to_read(project)


@router.put("/{project_id}", response_model=schemas.ProjectRead)
def update_project(
    project_id: int,
    payload: schemas.ProjectUpdate,
    user: User = Depends(auth.get_current_user),
    session: Session = Depends(get_session),
) -> schemas.ProjectRead:
    project = get_owned_project(project_id, user, session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    session.add(project)
    session.commit()
    session.refresh(project)
    return to_read(project)


@router.post("/{project_id}/publish", response_model=schemas.PublishResponse)
def publish_project(
    project_id: int,
    user: User = Depends(auth.get_current_user),
    session: Session = Depends(get_session),
) -> schemas.PublishResponse:
    project = get_owned_project(project_id, user, session)

    # Deterministic publish requirements. The AI score is never a gate.
    if not project.title.strip():
        raise HTTPException(status_code=400, detail="add a title before publishing")
    if project.price_inr < 0:
        raise HTTPException(status_code=400, detail="price cannot be negative")
    if not project.demo_url.strip() and not project.file_path:
        raise HTTPException(status_code=400, detail="add a demo link or upload the project ZIP")
    if project.ai_review is None:
        raise HTTPException(status_code=400, detail="run the quality check before publishing")

    project.status = "published"
    session.add(project)
    session.commit()
    session.refresh(project)
    return schemas.PublishResponse(id=project.id, status=project.status)


@router.post("/{project_id}/file", response_model=schemas.ProjectRead)
async def upload_project_file(
    project_id: int,
    file: UploadFile = File(...),
    user: User = Depends(auth.get_current_user),
    session: Session = Depends(get_session),
) -> schemas.ProjectRead:
    """Attach the ZIP buyers download. Replacing an upload deletes the old file."""
    project = get_owned_project(project_id, user, session)
    file_name, _size = await storage.save_zip(project_id, file)
    storage.delete_zip(project.file_path)
    project.file_path = file_name
    session.add(project)
    session.commit()
    session.refresh(project)
    return to_read(project)


@router.get("/{project_id}/download")
def download_project_file(
    project_id: int,
    user: User = Depends(auth.get_current_user),
    session: Session = Depends(get_session),
) -> FileResponse:
    """The paid buyer or the seller only."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    if project.seller_id != user.id:
        paid = session.exec(
            select(Order).where(
                Order.project_id == project.id,
                Order.buyer_id == user.id,
                Order.status == "paid",
            )
        ).first()
        if paid is None:
            raise HTTPException(status_code=403, detail="buy this project before downloading it")

    if not project.file_path:
        raise HTTPException(status_code=400, detail="the seller has not uploaded a ZIP yet")

    return FileResponse(
        storage.zip_path(project.file_path),
        media_type="application/zip",
        filename=zip_filename(project.title),
    )
