-- Migration: Add is_psc column to species table
-- Run this in Supabase SQL Editor

ALTER TABLE species ADD COLUMN IF NOT EXISTS is_psc BOOLEAN DEFAULT false;
