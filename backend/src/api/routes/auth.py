from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from src.api.deps import get_auth_service, get_current_user
from src.core.config import get_settings
from src.schemas.db import Users
from src.services.auth import AuthService


settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    """Request model for user registration."""

    name: str
    email: EmailStr
    password: str


class PasswordUpdate(BaseModel):
    """Request model for password changes."""

    old_password: str
    new_password: str


# Login and get JWT token, Endpoint
@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user and return JWT access token"""
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(user.user_id)

    response.set_cookie(
        key="auth_token",
        value=access_token,
        httponly=True,
        secure=False,  # Allow HTTP in development
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return {
        "message": "Login successful",
        "user": {
            "id": str(user.user_id),
            "email": user.email,
            "name": user.name,
        },
    }


@router.post("/logout")
async def logout(response: Response):
    """Clear authentication cookie"""
    response.delete_cookie(
        key="auth_token",
        path="/",
    )
    return {"message": "Logged out successfully"}


# Sign up Endpoint
@router.post("/signup")
async def signup(
    response: Response,
    user: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user"""
    new_user = auth_service.register_user(
        name=user.name, email=user.email, password=user.password
    )

    access_token = auth_service.create_access_token(new_user.user_id)

    response.set_cookie(
        key="auth_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return {
        "message": "User created successfully",
        "user_id": str(new_user.user_id),
        "user": {
            "id": str(new_user.user_id),
            "email": new_user.email,
            "name": new_user.name,
        },
    }


@router.get("/me")
async def get_current_user_info(current_user: Users = Depends(get_current_user)):
    """Get current authenticated user info"""
    return {
        "id": str(current_user.user_id),
        "email": current_user.email,
        "name": current_user.name,
    }


@router.put("/password")
async def update_password(
    password_data: PasswordUpdate,
    current_user: Users = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Update user's password."""
    auth_service.change_password(
        user_id=current_user.user_id,
        old_password=password_data.old_password,
        new_password=password_data.new_password,
    )

    return {"message": "Password updated successfully"}
