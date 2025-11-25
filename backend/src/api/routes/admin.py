"""
Admin API routes for user management.

Handles user approval, rejection, and invitation.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from src.api.deps import get_admin_user, get_auth_service, get_db
from src.repo.user import UserRepo
from src.schemas.db import Users
from src.services.auth import AuthService


router = APIRouter(prefix="/admin", tags=["Admin"])


class UserInvite(BaseModel):
    """Request model for inviting a user."""

    name: str
    email: EmailStr


class UserResponse(BaseModel):
    """User response model."""

    user_id: str
    name: str
    email: str
    role: str
    status: str
    invited_by: str | None = None
    invited_at: str | None = None
    approved_at: str | None = None
    approved_by: str | None = None

    @classmethod
    def from_user(cls, user: Users) -> "UserResponse":
        """Create UserResponse from Users model."""
        return cls(
            user_id=str(user.user_id),
            name=user.name,
            email=user.email,
            role=user.role,
            status=user.status,
            invited_by=str(user.invited_by) if user.invited_by else None,
            invited_at=user.invited_at.isoformat() if user.invited_at else None,
            approved_at=user.approved_at.isoformat() if user.approved_at else None,
            approved_by=str(user.approved_by) if user.approved_by else None,
        )


@router.get("/users/pending")
async def list_pending_users(
    admin_user: Users = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """List all users with pending approval status."""
    user_repo = UserRepo(db)
    pending_users = user_repo.get_pending_users()
    return [UserResponse.from_user(user) for user in pending_users]


@router.get("/users")
async def list_all_users(
    admin_user: Users = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """List all users (admin only)."""
    user_repo = UserRepo(db)
    users = user_repo.get_all_users()
    return [UserResponse.from_user(user) for user in users]


@router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: UUID,
    admin_user: Users = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Approve a pending user."""
    user_repo = UserRepo(db)
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not pending (current status: {user.status})",
        )

    approved_user = user_repo.approve_user(user_id, admin_user.user_id)
    if not approved_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse.from_user(approved_user)


@router.post("/users/{user_id}/reject")
async def reject_user(
    user_id: UUID,
    admin_user: Users = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Reject a pending user."""
    user_repo = UserRepo(db)
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not pending (current status: {user.status})",
        )

    rejected_user = user_repo.reject_user(user_id)
    if not rejected_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse.from_user(rejected_user)


@router.post("/users/invite")
async def invite_user(
    invite_data: UserInvite,
    admin_user: Users = Depends(get_admin_user),
    auth_service: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    """
    Invite a new user by email.

    Creates a user account with pending status and records the invitation.
    The user will need to set their password when they first log in.
    For now, we'll create them with a temporary password that they must change.
    """
    import secrets
    import string

    from src.utils.email import is_northeastern_email

    # Validate Northeastern email
    if not is_northeastern_email(invite_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Northeastern University email addresses (@northeastern.edu) are allowed",
        )

    # Check if user already exists
    user_repo = UserRepo(db)
    if user_repo.email_exists(invite_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Generate a temporary password (user should change on first login)
    temp_password = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(16)
    )

    # Create user with invitation
    user = auth_service.register_user(
        name=invite_data.name,
        email=invite_data.email,
        password=temp_password,
        invited_by=admin_user.user_id,
    )

    # TODO: Send invitation email with temporary password
    # For now, return the temporary password (in production, send via email)

    return {
        "message": "User invited successfully",
        "user": UserResponse.from_user(user),
        "temporary_password": temp_password,  # Remove in production
    }


@router.post("/users/{user_id}/promote")
async def promote_to_admin(
    user_id: UUID,
    admin_user: Users = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Promote a user to admin role.

    Only approved users can be promoted. Cannot promote yourself.
    """
    user_repo = UserRepo(db)
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.user_id == admin_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot promote yourself",
        )

    if user.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User must be approved before promotion (current status: {user.status})",
        )

    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already an admin",
        )

    updated_user = user_repo.update_role(user_id, "admin")
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return {
        "message": "User promoted to admin successfully",
        "user": UserResponse.from_user(updated_user),
    }


@router.post("/users/{user_id}/demote")
async def demote_from_admin(
    user_id: UUID,
    admin_user: Users = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """
    Demote an admin user to regular user role.

    Cannot demote yourself. Cannot demote if it's the last admin.
    """
    user_repo = UserRepo(db)
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.user_id == admin_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote yourself",
        )

    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not an admin",
        )

    # Check if this is the last admin
    admin_count = user_repo.count_admins()
    if admin_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote the last admin. At least one admin must remain.",
        )

    updated_user = user_repo.update_role(user_id, "user")
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return {
        "message": "User demoted to regular user successfully",
        "user": UserResponse.from_user(updated_user),
    }
