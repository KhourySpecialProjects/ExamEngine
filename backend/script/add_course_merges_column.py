"""
Script to add course_merges column to existing datasets table.

This script safely adds the course_merges JSONB column to the datasets table
without dropping existing data.

Usage:
    python script/add_course_merges_column.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load .env from multiple possible locations
script_dir = Path(__file__).resolve().parent
root_dir = script_dir.parent.parent
load_dotenv(root_dir / ".env")
load_dotenv(script_dir.parent / ".env")
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")


def add_course_merges_column():
    """Add course_merges column to datasets table."""
    engine = create_engine(DATABASE_URL, echo=True)

    print("🔍 Checking if course_merges column exists...")

    # Check if column exists (PostgreSQL)
    if DATABASE_URL.startswith("postgresql"):
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'datasets' AND column_name = 'course_merges'
                """)
            )
            if result.fetchone():
                print("✅ Column 'course_merges' already exists. No changes needed.")
                return

        print("➕ Adding course_merges column to datasets table...")
        with engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS course_merges JSONB DEFAULT NULL")
            )
            conn.commit()
        print("✅ Column 'course_merges' added successfully!")

    # SQLite (limited support)
    elif DATABASE_URL.startswith("sqlite"):
        print("⚠️  SQLite detected. ALTER TABLE support is limited.")
        print("   For SQLite, you may need to recreate the table.")
        print("   Consider using reset_database.py if you can lose data.")
        print("   Or manually add the column if your SQLite version supports it:")
        print("   ALTER TABLE datasets ADD COLUMN course_merges TEXT DEFAULT NULL;")

    else:
        print(f"⚠️  Unknown database type: {DATABASE_URL}")
        print("   Please manually add the column using SQL:")
        print("   ALTER TABLE datasets ADD COLUMN course_merges JSONB DEFAULT NULL;")


if __name__ == "__main__":
    try:
        add_course_merges_column()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

