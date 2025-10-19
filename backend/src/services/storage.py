import shutil
import uuid
import json
from datetime import datetime
import pandas as pd
from pathlib import Path

from .validation import validate_csv_schema, get_file_statistics


BASE_DIR = Path(__file__).parent.parent.parent
DATASETS_DIR =  BASE_DIR / "datasets"

class StorageService:
    
    @staticmethod
    def create_dataset_directory():
        """Create new dataset directory"""
        dataset_id = str(uuid.uuid4())
        dataset_dir = DATASETS_DIR / dataset_id

        dataset_dir.mkdir(parents=True, exist_ok=True)
        return dataset_id, dataset_dir
    
    @staticmethod
    async def save_and_validate_file(upload_file, file_type, dataset_dir):
        """Save and validate uploaded file"""
        file_path = dataset_dir / f"{file_type}.csv"
        
        try:
            # Save file
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            
            # Read and validate
            df = pd.read_csv(file_path)
            
            # Check schema
            missing_cols = validate_csv_schema(df, file_type)
            if missing_cols:
                return None, f"Missing columns: {', '.join(missing_cols)}"
            
            # Get statistics
            file_size = file_path.stat().st_size
            stats = get_file_statistics(df, file_type, file_size, upload_file.filename)
            
            return stats, None
            
        except pd.errors.EmptyDataError:
            return None, "File is empty"
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    @staticmethod
    def save_metadata(dataset_id, dataset_dir, files_metadata):
        """Save dataset metadata"""
        metadata = {
            'dataset_id': dataset_id,
            'created_at': datetime.now().isoformat(),
            'files': files_metadata,
            'status': 'uploaded',
        }
        
        metadata_path = dataset_dir / "metadata.json"
        with metadata_path.open("w") as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    @staticmethod
    def load_metadata(dataset_id):
        """Load metadata for dataset"""
        metadata_path = DATASETS_DIR / dataset_id / "metadata.json"
        
        if not metadata_path.exists():
            return None
        
        with metadata_path.open() as f:
            return json.load(f)
    
    @staticmethod
    def list_all_datasets():
        """List all datasets"""
        datasets = []
        
        if not DATASETS_DIR.exists():
            return []
        
        for dataset_dir in DATASETS_DIR.iterdir():
            if dataset_dir.is_dir():
                metadata_path = dataset_dir / "metadata.json"
                if metadata_path.exists():
                    with metadata_path.open() as f:
                        datasets.append(json.load(f))
        
        datasets.sort(key=lambda x: x['created_at'], reverse=True)
        return datasets
    
    @staticmethod
    def delete_dataset(dataset_id):
        """Delete dataset"""
        dataset_dir = DATASETS_DIR / dataset_id
        
        if not dataset_dir.exists():
            return False
        
        shutil.rmtree(dataset_dir)
        return True

    @staticmethod
    def get_dataset_by_id(dataset_id):
        """
        Get dataset by ID with full metadata
        
        Args:
            dataset_id: UUID of the dataset
            
        Returns:
            Dictionary with dataset metadata or None if not found
        """
        dataset_dir = DATASETS_DIR / dataset_id
        
        # Check if dataset exists
        if not dataset_dir.exists():
            return None
        
        # Load metadata
        metadata_path = dataset_dir / "metadata.json"
        if not metadata_path.exists():
            return None
        
        with metadata_path.open() as f:
            metadata = json.load(f)
        
        # Verify all CSV files exist
        expected_files = ['courses.csv', 'enrollments.csv', 'rooms.csv']
        for file_name in expected_files:
            file_path = dataset_dir / file_name
            if not file_path.exists():
                metadata['status'] = 'incomplete'
                metadata['error'] = f'Missing file: {file_name}'
        
        return metadata

    
