class AppExceptionError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, detail: dict | None = None):
        self.message = message
        self.detail = detail or {}
        super().__init__(self.message)


class DatasetNotFoundError(AppExceptionError):
    """Dataset doesn't exist or user lacks access."""

    pass


class DatasetDeletedError(AppExceptionError):
    """The dataset was deleted; its uploaded files are gone from storage."""

    pass


class ValidationError(AppExceptionError):
    """Input validation failed."""

    pass


class PlacementConflictError(AppExceptionError):
    """A late-add placement is no longer possible, or has unconfirmed conflicts."""

    pass


class DatasetExistsError(AppExceptionError):
    """Dataset of same name already exists"""

    pass


class StorageError(AppExceptionError):
    """S3 storage operation failed."""

    pass


class ScheduleGenerationError(AppExceptionError):
    """Schedule generation algorithm failed."""

    pass


class AuthenticationError(AppExceptionError):
    """User authentication failed."""

    pass


class AuthorizationError(AppExceptionError):
    """User lacks permission for operation."""

    pass
