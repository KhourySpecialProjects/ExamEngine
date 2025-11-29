"""
Email validation utilities.
"""


def is_northeastern_email(email: str) -> bool:
    """
    Validate that email is from Northeastern University domain.

    Args:
        email: Email address to validate

    Returns:
        True if email ends with @northeastern.edu (case-insensitive), False otherwise
    """
    if not email:
        return False
    return email.lower().strip().endswith("@northeastern.edu")

