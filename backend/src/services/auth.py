from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session
from src.schemas import db
from src.schemas.db import Users
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import os

# Config (use real env vars in production)
SECRET_KEY = "change-me-to-a-secure-random-string"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password, hashed_password):
    # Return True if passwords match, raise helpful HTTP errors on failures
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError as e:
        # e.g. input too long for bcrypt
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AttributeError as e:
        # bcrypt backend issue
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Password verification failed due to an incompatible bcrypt backend. "
                "Install a compatible package (pip install bcrypt or passlib[bcrypt]). "
                f"Original error: {e}"
            ),
        )


def get_password_hash(password):
    # Hash password, validate input length for bcrypt (72 bytes)
    try:
        pw_bytes = password.encode("utf-8") if isinstance(password, str) else bytes(password)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be a text string")

    if len(pw_bytes) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Password too long for bcrypt (over 72 bytes). Use a shorter password or a different hash."
            ),
        )

    try:
        return pwd_context.hash(password)
    except AttributeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Password hashing failed due to an incompatible bcrypt backend. "
                "Install a compatible package (pip install bcrypt or passlib[bcrypt]). "
                f"Original error: {e}"
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Simple DB session factory using same DB URL as db.main (adjust as needed)
def get_session():
    """Create and return a SQLAlchemy session.

    Uses DATABASE_URL or falls back to sqlite for local dev.
    Raises HTTP 503 if the DB can't be reached.
    """
    db_url = os.getenv("DATABASE_URL") or "sqlite:///./dev.db"
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    try:
        engine = create_engine(db_url, connect_args=connect_args)
        # quick connect to fail fast if DB is down
        with engine.connect() as conn:
            pass
    except OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Database connection failed. Check DATABASE_URL or start your Postgres server. "
                f"Original error: {exc}"
            ),
        )

    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def authenticate_user(username: str, password: str) -> Optional[Users]:
    # Try email first (unambiguous), then fallback to name.
    session = get_session()
    try:
        # 1) email lookup
        stmt = select(Users).where(Users.email == username)
        user = session.execute(stmt).scalars().first()
        if user:
            if verify_password(password, user.password_hash):
                return user
            return None

        # 2) fallback to name lookup — but check for ambiguity
        stmt2 = select(Users).where(Users.name == username)
        users = session.execute(stmt2).scalars().all()
        if not users:
            return None
        if len(users) > 1:
            # ambiguous username — require email or unique username
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Multiple accounts found with that name; please log in using your email address "
                    "instead or contact admin to set a unique username."
                ),
            )
        # single user matched by name
        user = users[0]
        if verify_password(password, user.password_hash):
            return user
        return None
    finally:
        session.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    session = get_session()
    try:
        stmt = select(Users).where(Users.user_id == user_id)
        user = session.execute(stmt).scalars().first()
        if user is None:
            raise credentials_exception
        return user
    finally:
        session.close()
