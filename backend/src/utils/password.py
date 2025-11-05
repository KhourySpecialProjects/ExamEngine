from fastapi import HTTPException, status
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against hashed version.

    Args:
        plain_password: User-provided password
        hashed_password: Stored password hash

    Returns:
        True if passwords match, False otherwise

    Raises:
        HTTPException: On bcrypt errors
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except AttributeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password verification failed: {e}",
        ) from e


def get_password_hash(password: str) -> str:
    """
    Hash password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt password hash

    Raises:
        HTTPException: If password is invalid or bcrypt fails
    """
    try:
        pw_bytes = (
            password.encode("utf-8") if isinstance(password, str) else bytes(password)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be a text string",
        ) from e

    if len(pw_bytes) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password too long for bcrypt (over 72 bytes)",
        )

    try:
        return pwd_context.hash(password)
    except AttributeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password hashing failed: {e}",
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
