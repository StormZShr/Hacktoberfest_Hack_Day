"""Password hashing, JWTs, and the `get_current_user` dependency."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

import config
from db import get_session
from models import User

# bcrypt refuses anything longer than 72 bytes.
MAX_PASSWORD_BYTES = 72

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=config.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Return the user id, or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None or not credentials.credentials:
        raise _unauthorized("missing bearer token")
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise _unauthorized("invalid or expired token")
    user = session.get(User, user_id)
    if user is None:
        raise _unauthorized("user no longer exists")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User | None:
    """For public pages that show the owner extra: anonymous is fine, no error."""
    if credentials is None or not credentials.credentials:
        return None
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        return None
    return session.get(User, user_id)
