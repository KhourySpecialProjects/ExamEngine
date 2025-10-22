from datetime import timedelta
from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from src.schemas.db import Users

from src.services.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    get_session,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Login and get JWT token, Endpoint
@router.post("/login")
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
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
    response.set_cookie(
            key="auth_token",
            value=access_token,
            httponly=True,   
            secure=True,   
            samesite="lax", 
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  
            path="/",
        )
    return {
            "message": "Login successful",
            "user": {
                "id": str(user.user_id),
                "email": user.email,
                "name": user.name,
            }
    }

@router.post("/logout")
async def logout(response: Response):
    """Clear authentication cookie"""
    response.delete_cookie(
        key="auth_token",
        path="/",
    )
    return {"message": "Logged out successfully"}


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


# Sign up Endpoint
@router.post("/signup")
async def signup(response: Response, user: UserCreate):
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

        # create acess token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(new_user.user_id)}, 
            expires_delta=access_token_expires
        )
        response.set_cookie(
            key="auth_token",
            value=access_token,
            httponly=True,   
            secure=True,   
            samesite="lax", 
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  
            path="/",
        )
        return {
            "message": "User created successfully", 
            "user_id": str(new_user.user_id),
            "user": {
                "id": str(new_user.user_id),
                "email": new_user.email,
                "name": new_user.name,
            }
        }
    finally:
        session.close()
@router.get("/me")
async def get_current_user_info(current_user: Users = Depends(get_current_user)):
    """Get current authenticated user info"""
    return {
        "id": str(current_user.user_id),
        "email": current_user.email,
        "name": current_user.name,
    }
