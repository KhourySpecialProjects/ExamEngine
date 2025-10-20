from datetime import timedelta
from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from src.schemas.db import Users

from src.services.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    get_session,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Login and get JWT token, Endpoint
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT access token"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=60 * 24)
    access_token = create_access_token(
        data={"sub": str(user.user_id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


# Sign up Endpoint
@router.post("/signup")
async def signup(user: UserCreate):
    """Register a new user"""
    session = get_session()
    try:
        existing_user = session.execute(
            select(Users).where(Users.email == user.email)
        ).scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        # create Users ORM instance and hash password
        new_user = Users(name=user.name, email=user.email, password_hash=get_password_hash(user.password))
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return {"message": "User created successfully", "user_id": str(new_user.user_id)}
    finally:
        session.close()