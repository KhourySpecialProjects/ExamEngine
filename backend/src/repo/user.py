from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schemas.db import Users

from .base import BaseRepo


class UserRepo(BaseRepo[Users]):
    """Repository for user data access operations."""

    def __init__(self, db: Session):
        super().__init__(Users, db)

    def get_by_id(self, user_id: UUID) -> Users | None:
        """Get user by ID."""
        stmt = select(Users).where(Users.user_id == user_id)
        return self.db.execute(stmt).scalars().first()

    def get_by_email(self, email: str) -> Users | None:
        """
        Find user by email address.

        Args:
            email: User's email address

        Returns:
            User object if found, None otherwise
        """
        stmt = select(Users).where(Users.email == email.lower())
        return self.db.execute(stmt).scalars().first()

    def get_by_name(self, name: str) -> Users | None:
        """Find first user by username."""
        stmt = select(Users).where(Users.name == name)
        return self.db.execute(stmt).scalars().first()

    def get_all_by_name(self, name: str) -> list[Users]:
        """
        Find all users with matching name.

        Used to detect duplicate usernames during authentication.
        """
        stmt = select(Users).where(Users.name == name)
        return list(self.db.execute(stmt).scalars().all())

    def email_exists(self, email: str) -> bool:
        """Check if email is already registered."""
        stmt = select(Users.user_id).where(Users.email == email.lower())
        result = self.db.execute(stmt).first()
        return result is not None

    def get_by_email_or_name(self, identifier: str) -> tuple[Users | None, bool]:
        """
        Find user by email or username with ambiguity detection.

        Args:
            identifier: Email or username

        Returns:
            Tuple of (user, is_ambiguous) where:
            - user: Found user or None
            - is_ambiguous: True if multiple users share this name
        """
        # Try email first
        user = self.get_by_email(identifier)
        if user:
            return user, False

        # Try username
        users = self.get_all_by_name(identifier)
        if len(users) == 0:
            return None, False
        elif len(users) == 1:
            return users[0], False
        else:
            return None, True  # Ambiguous

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: str = "user",
        status: str = "pending",
        invited_by: UUID | None = None,
    ) -> Users:
        """
        Create new user with hashed password and role/status.

        Args:
            name: User's display name
            email: User's email address
            password_hash: Hashed password
            role: User role ("admin" or "user")
            status: User status ("pending", "approved", or "rejected")
            invited_by: Optional user ID who invited this user

        Returns:
            Created user
        """
        from datetime import datetime

        user = Users(
            name=name,
            email=email.lower(),
            password_hash=password_hash,
            role=role,
            status=status,
            invited_by=invited_by,
            invited_at=datetime.now() if invited_by else None,
        )
        return self.create(user)

    def get_pending_users(self) -> list[Users]:
        """Get all users with pending status."""
        stmt = select(Users).where(Users.status == "pending").order_by(Users.email)
        return list(self.db.execute(stmt).scalars().all())

    def get_all_users(self) -> list[Users]:
        """Get all users."""
        stmt = select(Users).order_by(Users.email)
        return list(self.db.execute(stmt).scalars().all())

    def approve_user(self, user_id: UUID, approved_by: UUID) -> Users | None:
        """
        Approve a pending user.

        Args:
            user_id: User to approve
            approved_by: Admin user ID who is approving

        Returns:
            Updated user or None if not found
        """
        from datetime import datetime

        user = self.get_by_id(user_id)
        if user:
            user.status = "approved"
            user.approved_at = datetime.now()
            user.approved_by = approved_by
            return self.update(user)
        return None

    def reject_user(self, user_id: UUID) -> Users | None:
        """
        Reject a pending user.

        Args:
            user_id: User to reject

        Returns:
            Updated user or None if not found
        """
        user = self.get_by_id(user_id)
        if user:
            user.status = "rejected"
            return self.update(user)
        return None

    def update_password(self, user_id: UUID, new_password_hash: str) -> Users | None:
        """Update user's password hash."""
        user = self.get_by_id(user_id)
        if user:
            user.password_hash = new_password_hash
            return self.update(user)
        return None

    def update_role(self, user_id: UUID, new_role: str) -> Users | None:
        """
        Update user's role.

        Args:
            user_id: User to update
            new_role: New role ("admin" or "user")

        Returns:
            Updated user or None if not found
        """
        user = self.get_by_id(user_id)
        if user:
            user.role = new_role
            return self.update(user)
        return None

    def count_admins(self) -> int:
        """Count the number of admin users."""
        stmt = select(Users).where(Users.role == "admin")
        return len(list(self.db.execute(stmt).scalars().all()))
