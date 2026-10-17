"""Auth endpoints: register, login, and the current user."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

import auth
import schemas
from db import get_session
from models import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _clean_email(email: str) -> str:
    cleaned = email.strip().lower()
    if "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
        raise HTTPException(status_code=400, detail="enter a valid email address")
    return cleaned


@router.post("/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.RegisterRequest, session: Session = Depends(get_session)) -> schemas.TokenResponse:
    email = _clean_email(payload.email)
    if len(payload.password.encode("utf-8")) > auth.MAX_PASSWORD_BYTES:
        raise HTTPException(status_code=400, detail="password is too long")

    existing = session.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="that email is already registered")

    user = User(
        email=email,
        name=payload.name.strip(),
        password_hash=auth.hash_password(payload.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return schemas.TokenResponse(access_token=auth.create_access_token(user.id))


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, session: Session = Depends(get_session)) -> schemas.TokenResponse:
    email = _clean_email(payload.email)
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="wrong email or password")
    return schemas.TokenResponse(access_token=auth.create_access_token(user.id))


@router.get("/me", response_model=schemas.UserRead)
def me(user: User = Depends(auth.get_current_user)) -> User:
    return user
