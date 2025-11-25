class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, detail: dict | None = None):
        self.message = message
        self.detail = detail or {}
        super().__init__(self.message)


class DatasetNotFoundError(AppException):
    """Dataset doesn't exist or user lacks access."""

    pass


class ValidationError(AppException):
    """Input validation failed."""

    pass


class DatasetExistsError(AppException):
    """Dataset of same name already exists"""

    pass


class StorageError(AppException):
    """S3 storage operation failed."""

    pass


class ScheduleGenerationError(AppException):
    """Schedule generation algorithm failed."""

    pass


class AuthenticationError(AppException):
    """User authentication failed."""

    pass


class AuthorizationError(AppException):
    """User lacks permission for operation."""

    pass
