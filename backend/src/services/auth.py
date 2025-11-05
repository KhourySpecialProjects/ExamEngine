from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError, jwt

from src.core.config import get_settings
from src.repo.user import UserRepo
from src.schemas.db import Users
from src.utils.password import get_password_hash, verify_password


settings = get_settings()


class AuthService:
    """
    Authentication business logic service.

    Handles all authentication operations including:
    - User authentication with password verification
    - User registration
    - JWT token creation and verification
    - Password management
    """

    def __init__(self, user_repo: UserRepo):
        self.user_repo = user_repo

    def authenticate_user(self, username: str, password: str) -> Users | None:
        """
        Authenticate user by email or username with password verification.

        Args:
            username: Email or username
            password: Plain text password

        Returns:
            User object if authenticated, None otherwise

        Raises:
            HTTPException: If username is ambiguous
        """
        # Use repository to find user
        user, is_ambiguous = self.user_repo.get_by_email_or_name(username)

        if is_ambiguous:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple accounts found - please use email address",
            )

        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return user

    def register_user(self, name: str, email: str, password: str) -> Users:
        """
        Register new user with validation and password hashing.

        Args:
            name: User's display name
            email: User's email address
            password: Plain text password

        Returns:
            Newly created User

        Raises:
            HTTPException: If email already exists
        """
        # Check email availability
        if self.user_repo.email_exists(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash password
        password_hash = get_password_hash(password)

        # Create user
        return self.user_repo.create_user(
            name=name, email=email, password_hash=password_hash
        )

    def create_access_token(
        self, user_id: UUID, expires_delta: timedelta | None = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            user_id: User ID to encode in token
            expires_delta: Optional custom expiration

        Returns:
            JWT token string
        """
        to_encode = {"sub": str(user_id)}

        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(
                minutes=settings.access_token_expire_minutes
            )

        to_encode.update({"exp": expire})

        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    def verify_token(self, token: str) -> UUID | None:
        """
        Verify JWT token and extract user ID.

        Args:
            token: JWT token string

        Returns:
            User ID if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            user_id_str: str = payload.get("sub")
            if user_id_str is None:
                return None
            return UUID(user_id_str)
        except JWTError:
            return None

    def get_user_from_token(self, token: str) -> Users | None:
        """
        Get user from JWT token.

        Args:
            token: JWT token string

        Returns:
            User if token is valid, None otherwise
        """
        user_id = self.verify_token(token)
        if not user_id:
            return None
        return self.user_repo.get_by_id(user_id)

    def change_password(
        self, user_id: UUID, old_password: str, new_password: str
    ) -> Users:
        """
        Change password with old password verification.

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            Updated user

        Raises:
            HTTPException: If user not found or old password wrong
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if not verify_password(old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        new_hash = get_password_hash(new_password)
        updated_user = self.user_repo.update_password(user_id, new_hash)

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return updated_user
