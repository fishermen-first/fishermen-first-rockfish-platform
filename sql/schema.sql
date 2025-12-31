-- Fishermen First Analytics Platform
-- Database Schema for Supabase (PostgreSQL)

-- ============================================
-- Reference Tables
-- ============================================

-- Users table (extends Supabase Auth)
-- Stores additional user metadata beyond what Supabase Auth provides
CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL UNIQUE,
    role text NOT NULL CHECK (role IN ('admin', 'co_op_manager')),
    created_at timestamp with time zone DEFAULT now()
);

-- Seasons table
-- Defines fishing seasons by year with start and end dates
CREATE TABLE seasons (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    year integer NOT NULL UNIQUE,
    start_date date NOT NULL,
    end_date date NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

-- Species table
-- Reference list of fish species, including prohibited species catch (PSC)
CREATE TABLE species (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    species_code text NOT NULL UNIQUE,
    species_name text NOT NULL,
    is_psc boolean NOT NULL DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);

-- Processors table
-- Fish processing facilities that receive harvests
CREATE TABLE processors (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    processor_name text NOT NULL,
    contact_info text,
    created_at timestamp with time zone DEFAULT now()
);

-- ============================================
-- Core Entities
-- ============================================

-- Cooperatives table
-- Fishing cooperatives that participate in the Rockfish Program
CREATE TABLE cooperatives (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cooperative_name text NOT NULL,
    contact_info text,
    created_at timestamp with time zone DEFAULT now()
);

-- Members table
-- Individual members who belong to cooperatives
CREATE TABLE members (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    member_name text NOT NULL,
    contact_info text,
    created_at timestamp with time zone DEFAULT now()
);

-- Vessels table
-- Fishing vessels owned by members
CREATE TABLE vessels (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id uuid NOT NULL REFERENCES members(id),
    vessel_name text NOT NULL,
    vessel_id_number text NOT NULL UNIQUE,
    created_at timestamp with time zone DEFAULT now()
);

-- ============================================
-- Relationship Tables (Historical Tracking)
-- ============================================

-- Cooperative memberships table
-- Tracks which members belong to which cooperatives over time
-- effective_to = NULL means the membership is current
CREATE TABLE cooperative_memberships (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id uuid NOT NULL REFERENCES members(id),
    cooperative_id uuid NOT NULL REFERENCES cooperatives(id),
    effective_from date NOT NULL,
    effective_to date,
    created_at timestamp with time zone DEFAULT now()
);

-- Vessel cooperative assignments table
-- Tracks which vessels are assigned to which cooperatives over time
-- effective_to = NULL means the assignment is current
CREATE TABLE vessel_cooperative_assignments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id uuid NOT NULL REFERENCES vessels(id),
    cooperative_id uuid NOT NULL REFERENCES cooperatives(id),
    effective_from date NOT NULL,
    effective_to date,
    created_at timestamp with time zone DEFAULT now()
);

-- ============================================
-- Quota & Limits
-- ============================================

-- Quota allocations table
-- Stores quota amounts allocated to cooperatives, members, or vessels per season
-- member_id and vessel_id are optional for different allocation levels
CREATE TABLE quota_allocations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    season_id uuid NOT NULL REFERENCES seasons(id),
    cooperative_id uuid NOT NULL REFERENCES cooperatives(id),
    member_id uuid REFERENCES members(id),
    vessel_id uuid REFERENCES vessels(id),
    species_id uuid NOT NULL REFERENCES species(id),
    amount numeric NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

-- Quota transfers table
-- Records transfers of quota between cooperatives or members
CREATE TABLE quota_transfers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    season_id uuid NOT NULL REFERENCES seasons(id),
    from_cooperative_id uuid REFERENCES cooperatives(id),
    from_member_id uuid REFERENCES members(id),
    to_cooperative_id uuid REFERENCES cooperatives(id),
    to_member_id uuid REFERENCES members(id),
    species_id uuid NOT NULL REFERENCES species(id),
    amount numeric NOT NULL,
    transfer_date date NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

-- PSC limits table
-- Prohibited species catch limits per cooperative per season
CREATE TABLE psc_limits (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    season_id uuid NOT NULL REFERENCES seasons(id),
    cooperative_id uuid NOT NULL REFERENCES cooperatives(id),
    species_id uuid NOT NULL REFERENCES species(id),
    limit_amount numeric NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

-- ============================================
-- Transactional Data
-- ============================================

-- Harvests table
-- Records of fish harvested by vessels
CREATE TABLE harvests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    season_id uuid NOT NULL REFERENCES seasons(id),
    vessel_id uuid NOT NULL REFERENCES vessels(id),
    processor_id uuid REFERENCES processors(id),
    species_id uuid NOT NULL REFERENCES species(id),
    amount numeric NOT NULL,
    landed_date date NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

-- PSC events table
-- Records of prohibited species catch incidents
CREATE TABLE psc_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    season_id uuid NOT NULL REFERENCES seasons(id),
    vessel_id uuid NOT NULL REFERENCES vessels(id),
    cooperative_id uuid NOT NULL REFERENCES cooperatives(id),
    species_id uuid NOT NULL REFERENCES species(id),
    amount numeric NOT NULL,
    event_date date NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

-- ============================================
-- File Management
-- ============================================

-- File uploads table
-- Tracks files uploaded to Supabase Storage
CREATE TABLE file_uploads (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cooperative_id uuid NOT NULL REFERENCES cooperatives(id),
    uploaded_by uuid NOT NULL REFERENCES users(id),
    source_type text NOT NULL CHECK (source_type IN ('eFish', 'eLandings', 'fish_ticket', 'VMS')),
    filename text NOT NULL,
    storage_path text NOT NULL,
    row_count integer,
    status text NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'imported', 'error')),
    uploaded_at timestamp with time zone DEFAULT now()
);
