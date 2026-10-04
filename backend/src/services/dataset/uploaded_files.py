"""Download a dataset's uploaded files and parse them unfiltered.

Shared by the Schedule Validator and late add. Unlike generation's loaders
(`drop_zero_enrollment`, `DatasetFactory`), nothing is dropped: enrollments
keep every CRN, including CRNs that are not in the courses file.
"""

import asyncio
import logging

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
