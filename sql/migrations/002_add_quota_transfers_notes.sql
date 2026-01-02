-- Migration: Add notes column to quota_transfers table
-- Run this in Supabase SQL Editor

ALTER TABLE quota_transfers ADD COLUMN IF NOT EXISTS notes text;
