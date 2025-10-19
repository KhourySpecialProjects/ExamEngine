import pandas as pd

# Expected columns for each file type
EXPECTED_SCHEMAS = {
    'courses': ['CRN', 'course_ref', 'Course_Subject_Code', 'Course_Number', 'num_students'],
    'enrollments': ['student_id', 'CRN'],
    'rooms': ['room_name', 'capacity']
}

def validate_csv_schema(df, file_type):
    """Check if CSV has expected columns"""
    expected_cols = EXPECTED_SCHEMAS.get(file_type, [])
    missing_cols = [col for col in expected_cols if col not in df.columns]
    return missing_cols

def get_file_statistics(df, file_type, file_size, filename):
    """Get statistics for a file"""
    stats = {
        'filename': filename,
        'rows': len(df),
        'columns': list(df.columns),
        'size_bytes': file_size
    }
    
    if file_type == 'courses':
        stats['unique_crns'] = int(df['CRN'].nunique())
        stats['total_students'] = int(df['num_students'].sum())
        stats['avg_class_size'] = float(df['num_students'].mean())
        stats['subjects'] = int(df['Course_Subject_Code'].nunique())
        
    elif file_type == 'enrollments':
        stats['unique_students'] = int(df['student_id'].nunique())
        stats['unique_crns'] = int(df['CRN'].nunique())
        stats['total_enrollments'] = len(df)
        
    elif file_type == 'rooms':
        stats['unique_rooms'] = int(df['room_name'].nunique())
        stats['total_capacity'] = int(df['capacity'].sum())
        stats['avg_capacity'] = float(df['capacity'].mean())
        stats['max_capacity'] = int(df['capacity'].max())
    
    return stats
