-- Migration script to add course_merges column to datasets table
-- Run this on your production database to add the new column without losing data

-- For PostgreSQL
ALTER TABLE datasets 
ADD COLUMN IF NOT EXISTS course_merges JSONB DEFAULT NULL;

-- For SQLite (if using SQLite in production - not recommended)
-- Note: SQLite has limited ALTER TABLE support, may need table recreation
-- ALTER TABLE datasets ADD COLUMN course_merges TEXT DEFAULT NULL;

-- Verify the column was added
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'datasets' AND column_name = 'course_merges';

