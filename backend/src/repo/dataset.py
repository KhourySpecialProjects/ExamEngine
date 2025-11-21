from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schemas.db import Datasets

from .base import BaseRepo


class DatasetRepo(BaseRepo[Datasets]):
    """Repository for dataset data access operations."""

    def __init__(self, db: Session):
        super().__init__(Datasets, db)

    def get_by_id(self, dataset_id: UUID) -> Datasets | None:
        """Get dataset by ID."""
        stmt = select(Datasets).where(Datasets.dataset_id == dataset_id)
        return self.db.execute(stmt).scalars().first()

    def get_by_id_for_user(self, dataset_id: UUID, user_id: UUID) -> Datasets | None:
        """
        Get dataset with authorization check.

        Ensures user can only access their own datasets.
        """
        stmt = select(Datasets).where(
            Datasets.dataset_id == dataset_id, Datasets.user_id == user_id
        )
        return self.db.execute(stmt).scalars().first()

    def get_all_for_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Datasets]:
        """Get all datasets for a user with pagination."""
        stmt = (
            select(Datasets)
            .where(Datasets.user_id == user_id, Datasets.deleted_at.is_(None))
            .order_by(Datasets.upload_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_name_for_user(self, dataset_name: str, user_id: UUID) -> Datasets | None:
        """Find dataset by name for specific user."""
        stmt = select(Datasets).where(
            Datasets.dataset_name == dataset_name, Datasets.user_id == user_id
        )
        return self.db.execute(stmt).scalars().first()

    def soft_delete(self, dataset_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete a dataset - marks as deleted in database only.
        """
        # Check if the dataset exists
        stmt = select(Datasets).where(
            Datasets.dataset_id == dataset_id,
            Datasets.user_id == user_id,
            Datasets.deleted_at.is_(None),  # Only delete non-deleted datasets
        )
        dataset = self.db.execute(stmt).scalars().first()

        if not dataset:
            return False

        dataset.deleted_at = datetime.now()
        self.db.commit()
        self.db.refresh(dataset)

        return True
