from fastapi import APIRouter, UploadFile, File, HTTPException, Form

import shutil
import uuid
from src.services.storage import StorageService

router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.post("/upload")
async def upload_dataset(
    dataset_name: str = Form(None),
    courses: UploadFile = File(...),
    enrollments: UploadFile = File(...),
    rooms: UploadFile = File(...)
):
    

        
        uploaded_files = {
            'ClassCensus': courses,
            'Enrollments': enrollments,
            'Classrooms': rooms
        }
        
        new_uuid = str(uuid.uuid4())
        
        ###
        validation_errors = {}
        uploaded = {}
        # Process each file
        for file_type, upload_file in uploaded_files.items():
            error, stats = await StorageService.save_and_validate_file(
                upload_file, file_type, new_uuid
            )
        if error:
            validation_errors[file_type] = error
        else:
            uploaded[file_type] = stats

        if validation_errors:

            raise HTTPException(
                status_code=400,
                detail={"message": "Validation failed", "errors": validation_errors},
            )

        return {
            "dataset_id": new_uuid,
            "dataset_name": dataset_name,
            "status": "uploaded",
            "files": uploaded,  # contains whatever stats you return (s3_key, bytes, etc.)
        }
@router.get("")
async def list_datasets():
    """List all datasets"""
    return StorageService.list_all_datasets()


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str):
    """Get dataset metadata"""
    metadata = StorageService.get_dataset_by_id(dataset_id)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return metadata


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete dataset"""
    success = StorageService.delete_dataset(dataset_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return {"message": "Dataset deleted", "dataset_id": dataset_id}
