from abc import ABC, abstractmethod
from typing import Optional, Tuple


class IStorage(ABC):
    """
    Abstract base class for storage

    This interface defines operations for file storage
    Implementation can use S3, local filesystem, etc
    """
    @abstractmethod
    async def upload_file(
            self, 
            file_content: bytes,
            key: str,
            content_type: str = "text/csv"
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Upload a file to storage. 
        """
        pass

    @abstractmethod
    def download_file(self, key: str) -> Optional[bytes]: 
        """
        Download a file from storage
        """
        pass

    @abstractmethod
    def delete_file(self, key: str) -> bool: 
        """
        Delete a single file from storage
        """
        pass

    @abstractmethod
    def delete_directory(self, prefix: str) -> bool:
        """
        Delete all files with a given prefix (directory).
        """
        pass

    @abstractmethod
    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in storage.
        """
        pass

