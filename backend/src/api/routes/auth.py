from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from src.api.deps import get_auth_service, get_current_user, get_db
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
            "role": user.role,
            "status": user.status,
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
            "role": new_user.role,
            "status": new_user.status,
        },
    }


@router.get("/me")
async def get_current_user_info(current_user: Users = Depends(get_current_user)):
    """Get current authenticated user info"""
    return {
        "id": str(current_user.user_id),
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "status": current_user.status,
    }


@router.get("/users/approved")
async def get_approved_users(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get list of all approved users.
    This endpoint is available to all authenticated users for sharing purposes.
    """
    from src.repo.user import UserRepo

    user_repo = UserRepo(db)
    approved_users = user_repo.get_all_users()
    # Filter to only approved users
    approved = [u for u in approved_users if u.status == "approved"]

    return [
        {
            "user_id": str(u.user_id),
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "status": u.status,
        }
        for u in approved
    ]


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
