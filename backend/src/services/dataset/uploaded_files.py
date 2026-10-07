"""Download a dataset's uploaded files and parse them unfiltered.

Shared by the Schedule Validator and late add. Unlike generation's loaders
(`drop_zero_enrollment`, `DatasetFactory`), nothing is dropped: enrollments
keep every CRN, including CRNs that are not in the courses file. Both also read
the dataset's stored combined/common groups through `stored_groups`, so they
build exam units and time groups from the same CRN strings. Lookups that need
one file (person exams, the Explore tab's rooms) use `download_uploaded_file`.
"""

import asyncio
import logging
from collections.abc import Mapping

from src.core.exceptions import StorageError
from src.domain.validation import DatasetFiles, parse_dataset_files
from src.domain.validation.snapshot import COURSES, ENROLLMENTS, ROOM_BLOCKOUTS, ROOMS
from src.schemas.db import Datasets
from src.services.dataset.service import entry_type
from src.services.storage.interface import IStorage


logger = logging.getLogger("examengine.dataset_files")

_LOADED_FILES = (COURSES, ENROLLMENTS, ROOMS, ROOM_BLOCKOUTS)


async def load_uploaded_files(
    dataset: Datasets | None, storage: IStorage, context: str
) -> DatasetFiles | None:
    """Download and parse the dataset's courses, enrollments, rooms and blockouts.

    None when the dataset is missing or deleted (its files are deleted from
    storage with it) or any of its files cannot be downloaded. `context` starts
    the log messages, e.g. "Validation of schedule <id>".
    """
    if dataset is None or dataset.deleted_at is not None:
        return None
    keys = {
        entry_type(entry): entry["storage_key"]
        for entry in dataset.file_paths
        if entry_type(entry) in _LOADED_FILES
    }
    try:
        contents = await asyncio.gather(
            *(asyncio.to_thread(storage.download_file, key) for key in keys.values())
        )
    except Exception:
        logger.warning(
            "%s: downloading dataset %s files failed",
            context,
            dataset.dataset_id,
            exc_info=True,
        )
        return None
    downloaded = dict(zip(keys, contents, strict=True))
    missing = sorted(file_type for file_type, data in downloaded.items() if not data)
    if missing:
        logger.warning(
            "%s: dataset %s files not available: %s",
            context,
            dataset.dataset_id,
            ", ".join(missing),
        )
        return None
    return await asyncio.to_thread(parse_dataset_files, downloaded)


async def download_uploaded_file(
    dataset: Datasets, storage: IStorage, file_type: str, context: str
) -> bytes | None:
    """One uploaded file's contents; None when the dataset has no such file.

    Raises `StorageError` when the dataset was deleted (its files are deleted
    from storage with it) or the file can't be downloaded. `context` starts the
    log messages, e.g. "Person exams on schedule <id>".
    """
    if dataset.deleted_at is not None:
        raise StorageError(f"Dataset {dataset.dataset_id} was deleted.")
    key = next(
        (
            entry["storage_key"]
            for entry in dataset.file_paths
            if entry_type(entry) == file_type
        ),
        None,
    )
    if key is None:
        return None
    try:
        content = await asyncio.to_thread(storage.download_file, key)
    except Exception as exc:
        logger.warning(
            "%s: downloading dataset %s %s file failed",
            context,
            dataset.dataset_id,
            file_type,
            exc_info=True,
        )
        raise StorageError(f"Could not download the {file_type} file.") from exc
    if not content:
        logger.warning(
            "%s: dataset %s %s file not available",
            context,
            dataset.dataset_id,
            file_type,
        )
        raise StorageError(f"The {file_type} file is not available.")
    return content


def stored_groups(groups: Mapping[str, list[str]] | None) -> dict[str, tuple[str, ...]]:
    """A dataset's stored combined or common groups: label -> CRNs."""
    return {
        str(label): tuple(str(crn) for crn in crns)
        for label, crns in (groups or {}).items()
    }
