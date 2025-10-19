from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil

from src.services.storage import StorageService

router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.post("/upload")
async def upload_dataset(
    courses: UploadFile = File(...),
    enrollments: UploadFile = File(...),
    rooms: UploadFile = File(...)
):
    """Upload dataset CSVs"""
    dataset_id, dataset_dir = StorageService.create_dataset_directory()
    
    try:
        files_metadata = {}
        validation_errors = {}
        
        uploaded_files = {
            'courses': courses,
            'enrollments': enrollments,
            'rooms': rooms
        }
        
        # Process each file
        for file_type, upload_file in uploaded_files.items():
            stats, error = await StorageService.save_and_validate_file(
                upload_file, file_type, dataset_dir
            )
            
            if error:
                validation_errors[file_type] = error
            else:
                files_metadata[file_type] = stats
        
        # If validation failed, clean up
        if validation_errors:
            shutil.rmtree(dataset_dir)
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Validation failed",
                    "errors": validation_errors
                }
            )
        
        # Save metadata
        metadata = StorageService.save_metadata(dataset_id, dataset_dir, files_metadata)
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


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
