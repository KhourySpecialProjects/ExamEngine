class DomainExceptionError(Exception):
    """Base for all domain errors."""

    pass


class SchemaDetectionError(DomainExceptionError):
    """CSV doesn't match any known schema."""

    pass


class DataValidationError(DomainExceptionError):
    """Data fails validation rules."""

    pass


class SchedulingError(DomainExceptionError):
    """Schedule generation failed."""

    pass
