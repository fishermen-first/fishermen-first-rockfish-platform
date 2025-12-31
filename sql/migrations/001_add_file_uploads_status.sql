-- Migration: Add status column to file_uploads table
-- Run this in Supabase SQL Editor if you have existing data

-- Add status column with default value
ALTER TABLE file_uploads
ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'uploaded';

-- Add check constraint
ALTER TABLE file_uploads
ADD CONSTRAINT file_uploads_status_check
CHECK (status IN ('uploaded', 'imported', 'error'));

-- Update any existing records to have 'uploaded' status (already handled by DEFAULT)
