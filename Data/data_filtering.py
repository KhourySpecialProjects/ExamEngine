#!/usr/bin/env python3
"""
Data Filtering Script for ExamEngine

This script processes and cleans data files to create three output CSV files:
1. new_classrooms.csv - from SpListing.xlsx.csv
2. new_classcensus.csv - from Fall2025FinalExams.csv and DB_ST_Class-Census
3. new_enrollments.csv - from DB_ST_Enrollment

Author: ExamEngine Team
Date: 2025
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Tuple

def load_data_files() -> Dict[str, pd.DataFrame]:
    """Load all required data files into DataFrames."""
    print("Loading data files...")
    
    data_files = {
        'fall2025_exams': pd.read_csv('Fall2025FinalExams.csv'),
        'class_census': pd.read_csv('DB_ST_Class-Census ExamEngine_20250919_105424.csv'),
        'enrollment': pd.read_csv('DB_ST_Enrollment-Census ExamEngine_20250919_113535.csv'),
        'sp_listing': pd.read_csv('SpListing.xlsx.csv')
    }
    
    print(f"Loaded {len(data_files)} data files")
    for name, df in data_files.items():
        print(f"  {name}: {df.shape[0]} rows, {df.shape[1]} columns")
    
    return data_files

def process_sp_listing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process SpListing data to create new_classrooms.csv
    Keep only Location Formal Name and Capacity columns, rename to room_name and capacity
    """
    print("\nProcessing SpListing data...")
    
    # Skip the header rows and get the actual data
    # The data starts from row 3 (0-indexed)
    data_df = df.iloc[2:].copy()  # Skip first 2 rows which are headers
    
    # Reset index
    data_df = data_df.reset_index(drop=True)
    
    # Select only the required columns (Location Formal Name and Capacity)
    # Based on the structure: Location Name, Location Formal Name, Capacity, Ratio, Shared, Campus Partition, Default Layout, Capacity
    new_classrooms = data_df.iloc[:, [1, 2]].copy()  # Location Formal Name (col 1) and Capacity (col 2)
    
    # Rename columns
    new_classrooms.columns = ['room_name', 'capacity']
    
    # Clean up the data - remove any rows with NaN values
    new_classrooms = new_classrooms.dropna()
    
    # Convert capacity to numeric, handling any non-numeric values
    new_classrooms['capacity'] = pd.to_numeric(new_classrooms['capacity'], errors='coerce')
    new_classrooms = new_classrooms.dropna()
    
    # Convert capacity to integer
    new_classrooms['capacity'] = new_classrooms['capacity'].astype(int)
    
    print(f"Processed {len(new_classrooms)} classroom records")
    return new_classrooms

def process_fall2025_exams(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process Fall2025FinalExams data
    Keep CRN, CourseID, and Enrolled columns, rename Enrolled to num_students
    Filter out Oakland classes and classes with 0 students
    """
    print("\nProcessing Fall2025FinalExams data...")
    
    # Select required columns: CRN, Course ID, Enrolled
    fall2025_processed = df[['CRN', 'Course ID', 'Enrolled']].copy()
    
    # Rename Enrolled to num_students
    fall2025_processed = fall2025_processed.rename(columns={'Enrolled': 'num_students'})
    
    # Filter out Oakland classes (Campus != 'OAK')
    fall2025_processed = fall2025_processed[df['Campus'] != 'OAK']
    
    # Filter out classes with 0 students
    fall2025_processed = fall2025_processed[fall2025_processed['num_students'] > 0]
    
    print(f"Processed {len(fall2025_processed)} exam records (after filtering)")
    print(f"  Removed Oakland classes: {len(df[df['Campus'] == 'OAK'])}")
    print(f"  Removed classes with 0 students: {len(df[df['Enrolled'] == 0])}")
    
    return fall2025_processed

def process_class_census(df: pd.DataFrame, fall2025_crns: List[int]) -> pd.DataFrame:
    """
    Process DB_ST_Class-Census data
    Filter for academic period 202610 and match CRNs with Fall2025FinalExams
    Extract building and room information
    """
    print("\nProcessing DB_ST_Class-Census data...")
    
    # Filter for academic period 202610
    class_census_202610 = df[df['Academic_Period_NUFreeze'] == 202610].copy()
    
    # Filter for CRNs that exist in Fall2025FinalExams
    class_census_filtered = class_census_202610[
        class_census_202610['Course_Reference_Number'].isin(fall2025_crns)
    ].copy()
    
    # Select required columns and rename them
    class_census_processed = class_census_filtered[[
        'Course_Reference_Number', 'Course_Identification', 'Building', 'Room_Number'
    ]].copy()
    
    # Rename columns to match expected output
    class_census_processed = class_census_processed.rename(columns={
        'Course_Reference_Number': 'CRN',
        'Course_Identification': 'CourseID',
        'Building': 'building',
        'Room_Number': 'room_number'
    })
    
    print(f"Processed {len(class_census_processed)} class census records")
    print(f"  Total 202610 records: {len(class_census_202610)}")
    print(f"  Matched with Fall2025 CRNs: {len(class_census_filtered)}")
    
    return class_census_processed

def process_enrollments(df: pd.DataFrame, fall2025_crns: List[int], fall2025_instructors: pd.DataFrame) -> pd.DataFrame:
    """
    Process DB_ST_Enrollment data
    Filter for academic period 202610 and CRNs that exist in Fall2025FinalExams
    Keep Student_PIDM, CRN, and add instructor_name by matching with Fall2025FinalExams
    """
    print("\nProcessing DB_ST_Enrollment data...")
    
    # Filter for academic period 202610
    enrollments_202610 = df[df['Academic_Period'] == 202610].copy()
    
    # Filter for CRNs that exist in Fall2025FinalExams
    enrollments_filtered = enrollments_202610[
        enrollments_202610['Course_Reference_Number'].isin(fall2025_crns)
    ].copy()
    
    # Select required columns
    enrollments_processed = enrollments_filtered[[
        'Student_PIDM', 'Course_Reference_Number'
    ]].copy()
    
    # Rename columns
    enrollments_processed = enrollments_processed.rename(columns={
        'Course_Reference_Number': 'CRN'
    })
    
    # Add instructor names by merging with Fall2025FinalExams data
    instructor_mapping = fall2025_instructors[['CRN', 'Instructor Name']].copy()
    instructor_mapping = instructor_mapping.rename(columns={'Instructor Name': 'instructor_name'})
    
    enrollments_processed = enrollments_processed.merge(
        instructor_mapping, 
        on='CRN', 
        how='left'
    )
    
    print(f"Processed {len(enrollments_processed)} enrollment records")
    print(f"  Total 202610 records: {len(enrollments_202610)}")
    print(f"  Matched with Fall2025 CRNs: {len(enrollments_filtered)}")
    print(f"  Records with instructor names: {enrollments_processed['instructor_name'].notna().sum()}")
    
    return enrollments_processed

def merge_class_data(fall2025_df: pd.DataFrame, class_census_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge Fall2025FinalExams data with Class-Census data to fill in room information
    """
    print("\nMerging class data...")
    
    # Merge on CRN
    merged_class_data = fall2025_df.merge(
        class_census_df, 
        on='CRN', 
        how='left'
    )
    
    # Remove duplicate CourseID column (keep the one from fall2025_df)
    if 'CourseID' in merged_class_data.columns:
        # Drop the CourseID column from class_census_df (it's the second one)
        merged_class_data = merged_class_data.drop(columns=['CourseID'])
        # Rename the original CourseID to keep it
        merged_class_data = merged_class_data.rename(columns={'Course ID': 'CourseID'})
    
    # Check how many records got room information
    records_with_rooms = merged_class_data.dropna(subset=['building', 'room_number'])
    print(f"Records with room information: {len(records_with_rooms)}")
    print(f"Records without room information: {len(merged_class_data) - len(records_with_rooms)}")
    
    return merged_class_data

def save_output_files(new_classrooms: pd.DataFrame, 
                     new_classcensus: pd.DataFrame, 
                     new_enrollments: pd.DataFrame) -> None:
    """Save the processed data to CSV files."""
    print("\nSaving output files...")
    
    # Save new_classrooms.csv
    new_classrooms.to_csv('new_classrooms.csv', index=False)
    print(f"Saved new_classrooms.csv with {len(new_classrooms)} records")
    
    # Save new_classcensus.csv
    new_classcensus.to_csv('new_classcensus.csv', index=False)
    print(f"Saved new_classcensus.csv with {len(new_classcensus)} records")
    
    # Save new_enrollments.csv
    new_enrollments.to_csv('new_enrollments.csv', index=False)
    print(f"Saved new_enrollments.csv with {len(new_enrollments)} records")

def main():
    """Main function to orchestrate the data filtering process."""
    print("Starting data filtering process...")
    
    # Load all data files
    data_files = load_data_files()
    
    # Process SpListing to create new_classrooms
    new_classrooms = process_sp_listing(data_files['sp_listing'])
    
    # Process Fall2025FinalExams
    fall2025_processed = process_fall2025_exams(data_files['fall2025_exams'])
    
    # Get list of CRNs from Fall2025FinalExams for matching
    fall2025_crns = fall2025_processed['CRN'].tolist()
    print(f"\nFound {len(fall2025_crns)} unique CRNs in Fall2025FinalExams")
    
    # Process Class-Census data
    class_census_processed = process_class_census(data_files['class_census'], fall2025_crns)
    
    # Process Enrollment data (pass the original Fall2025FinalExams data for instructor mapping)
    enrollments_processed = process_enrollments(data_files['enrollment'], fall2025_crns, data_files['fall2025_exams'])
    
    # Merge class data to create new_classcensus
    new_classcensus = merge_class_data(fall2025_processed, class_census_processed)
    
    # Save all output files
    save_output_files(new_classrooms, new_classcensus, enrollments_processed)
    
    print("\nData filtering process completed successfully!")
    print("\nSummary:")
    print(f"  new_classrooms.csv: {len(new_classrooms)} records")
    print(f"  new_classcensus.csv: {len(new_classcensus)} records")
    print(f"  new_enrollments.csv: {len(enrollments_processed)} records")

if __name__ == "__main__":
    main()
