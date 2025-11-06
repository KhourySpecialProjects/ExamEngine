from typing import TypeVar

from sqlalchemy.orm import Session

from src.schemas.db import Base


ModelType = TypeVar("ModelType", bound=Base)


class BaseRepo[ModelType: Base]:
    """
    Base repository providing common database operations.
    """

    def __init__(self, model: type[ModelType], db: Session):
        """
        Initialize repository with model class and database session.

        Args:
            model: SQLAlchemy model class (e.g., Users, Datasets)
            db: Database session for executing queries
        """
        self.model = model
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Retrieve all records with pagination."""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj: ModelType) -> ModelType:
        """Create new record."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelType) -> ModelType:
        """Update existing record."""
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        """Delete record."""
        self.db.delete(obj)
        self.db.commit()
