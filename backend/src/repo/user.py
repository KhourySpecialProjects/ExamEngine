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

    def create_user(self, name: str, email: str, password_hash: str) -> Users:
        """Create new user with hashed password."""
        user = Users(name=name, email=email.lower(), password_hash=password_hash)
        return self.create(user)

    def update_password(self, user_id: UUID, new_password_hash: str) -> Users | None:
        """Update user's password hash."""
        user = self.get_by_id(user_id)
        if user:
            user.password_hash = new_password_hash
            return self.update(user)
        return None
