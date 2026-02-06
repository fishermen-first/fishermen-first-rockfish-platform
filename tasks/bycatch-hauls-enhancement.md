# Bycatch Alert Enhancements - Implementation Prompt

## Instructions

Enter plan mode and create an implementation plan for the bycatch alert enhancements described below. This comes from a client meeting where Chelsea and Danielle requested updates to the MVP.

First, create a new branch:
```bash
git checkout -b feature/bycatch-hauls-enhancement
```

---

## Context

The current bycatch alerts system supports a single location per alert. We need to support multiple hauls (tows) per alert with detailed timing, location, and depth data for each haul. This matches how fishermen record data in their logbooks.

### Current State
- `bycatch_alerts` table has single `latitude`, `longitude`, `amount` fields
- Coordinates stored as decimal degrees
- No time or depth tracking
- No RPCA (Rockfish Program Chinook Area) association

### Target State
- Multiple hauls per alert with full fishing operation data
- RPCA area lookup table for reporting linkage
- Coordinate format toggle (degrees/minutes vs decimal)
- Backwards compatibility with existing alerts

---

## Requirements

### 1. Multiple Hauls Support

- Allow unlimited hauls per alert (haul 1, haul 2, haul 3, etc.)
- Each haul has its own set of fields (see below)
- UI: "Add Haul" button to append new hauls
- UI: Allow removing hauls
- Store in separate `bycatch_hauls` table (NOT JSON) for queryability

### 2. Per-Haul Fields

| Field | Type | Notes |
|-------|------|-------|
| Haul number | Integer | Auto-increment per alert (1, 2, 3...) |
| Location name | Text | Free text for spot names ("Tater", "Shit Hole", etc.) |
| High salmon encounter | Boolean | Checkbox to flag hauls with high salmon bycatch |
| Set date | Date | When gear was deployed |
| Set time | Time | When gear was deployed |
| Set latitude | Decimal degrees | Store as NUMERIC(9,6) |
| Set longitude | Decimal degrees | Store as NUMERIC(10,6) |
| Retrieval date | Date | When gear was retrieved |
| Retrieval time | Time | When gear was retrieved |
| Retrieval latitude | Decimal degrees | Store as NUMERIC(9,6) |
| Retrieval longitude | Decimal degrees | Store as NUMERIC(10,6) |
| Bottom depth | Numeric | Fathoms - ocean floor depth |
| Sea depth | Numeric | Fathoms - depth gear was fishing |
| RPCA area | UUID FK | Rockfish Program Chinook Area (dropdown) |
| Amount | Numeric | Pounds (halibut) or count (salmon) - moved from alert level |

### 3. RPCA Areas Lookup Table

Create `rpca_areas` table:
- `id` UUID primary key
- `code` TEXT unique (e.g., "RPCA-1", "RPCA-2")
- `name` TEXT (human-readable name)
- Seed with placeholder values for now (real values TBD from inter-co-op agreement)

Purpose: Links hotspots to reporting areas for summarizing bycatch by location. When an area has too many hotspots, it gets closed to all fishing.

### 4. Coordinate Format Toggle

- UI toggle: "Degrees/Minutes" or "Decimal Degrees"
- Store as decimal degrees internally (current format)
- Convert on input/display based on user preference
- Use existing converter at `.claude/plugins/fishermen-first/skills/quota-reference/scripts/coordinate_converter.py` - copy to `app/utils/coordinates.py`

### 5. Update Email Notifications

When an alert is shared, include all haul details in the email:
- List each haul with its location name, coordinates, times, depths
- Flag hauls marked as high salmon encounter
- Include RPCA area code

### 6. Backwards Compatibility

Existing alerts must continue to work:
- Migration creates "haul 1" for each existing alert
- Move existing `latitude`, `longitude`, `amount` to the new haul record
- Old alerts display as having 1 haul
- Remove old columns from `bycatch_alerts` after migration

### 7. Quota Transfers Updates (Secondary)

While in this branch, also update transfers:
- Add secondary species: Shortraker, Rougheye, Thornyhead
- Add Halibut to transferable species
- Do NOT add Salmon (they don't transfer salmon)
- Add metric ton display (conversion factor: 2,204.62 lbs/MT) for e-fish reconciliation
- Ensure transfers track at co-op level (already have vessel→coop relationship)

---

## Database Schema

### New Tables

```sql
-- RPCA Areas lookup
CREATE TABLE rpca_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Bycatch hauls (one-to-many with bycatch_alerts)
CREATE TABLE bycatch_hauls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES bycatch_alerts(id) ON DELETE CASCADE,
    haul_number INTEGER NOT NULL,

    -- Location
    location_name TEXT,
    rpca_area_id UUID REFERENCES rpca_areas(id),

    -- Salmon flag
    high_salmon_encounter BOOLEAN DEFAULT false,

    -- Set (gear deployment)
    set_date DATE,
    set_time TIME,
    set_latitude NUMERIC(9,6),
    set_longitude NUMERIC(10,6),

    -- Retrieval
    retrieval_date DATE,
    retrieval_time TIME,
    retrieval_latitude NUMERIC(9,6),
    retrieval_longitude NUMERIC(10,6),

    -- Depths (fathoms)
    bottom_depth NUMERIC,
    sea_depth NUMERIC,

    -- Catch (moved from alert level)
    amount NUMERIC NOT NULL,

    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(alert_id, haul_number),

    -- Alaska coordinate validation
    CONSTRAINT valid_set_lat CHECK (set_latitude IS NULL OR set_latitude BETWEEN 50.0 AND 72.0),
    CONSTRAINT valid_set_lon CHECK (set_longitude IS NULL OR set_longitude BETWEEN -180.0 AND -130.0),
    CONSTRAINT valid_ret_lat CHECK (retrieval_latitude IS NULL OR retrieval_latitude BETWEEN 50.0 AND 72.0),
    CONSTRAINT valid_ret_lon CHECK (retrieval_longitude IS NULL OR retrieval_longitude BETWEEN -180.0 AND -130.0)
);
```

### Modify Existing Table

```sql
-- After hauls migration, remove old columns from bycatch_alerts
ALTER TABLE bycatch_alerts
    DROP COLUMN latitude,
    DROP COLUMN longitude,
    DROP COLUMN amount;

-- Add coordinate format preference (optional - could be user-level)
ALTER TABLE bycatch_alerts ADD COLUMN coordinate_format TEXT DEFAULT 'dms'
    CHECK (coordinate_format IN ('dms', 'decimal'));
```

### RLS Policies

Add RLS for new tables following existing patterns:
- `rpca_areas`: Read-only for all authenticated users in org
- `bycatch_hauls`: Same policies as parent `bycatch_alerts` (vessel owners see own, managers see all)

---

## Files to Modify/Create

| File | Action | Description |
|------|--------|-------------|
| `sql/migrations/012_bycatch_hauls.sql` | Create | Full migration with tables, RLS, backwards compat |
| `app/utils/coordinates.py` | Create | Copy from skill + any needed additions |
| `app/pages/3_🐟_Bycatch_Alerts.py` | Modify | Add hauls UI, coordinate toggle, RPCA dropdown |
| `app/services/email.py` | Modify | Include haul details in alert emails |
| `app/pages/4_🔄_Transfers.py` | Modify | Add species, MT conversion |

---

## UI Mockup (Conceptual)

```
┌─────────────────────────────────────────────────────────┐
│ Create Bycatch Alert                                    │
├─────────────────────────────────────────────────────────┤
│ Species: [Chinook Salmon ▼]    Vessel: [Arctic Ram ▼]  │
│                                                         │
│ Coordinate Format: ○ Degrees/Minutes  ● Decimal        │
├─────────────────────────────────────────────────────────┤
│ ┌─ Haul 1 ──────────────────────────────────── [✕] ─┐  │
│ │ Location Name: [Tater_____________]                │  │
│ │ RPCA Area: [RPCA-1 ▼]  ☑ High Salmon Encounter    │  │
│ │                                                    │  │
│ │ SET                      RETRIEVAL                 │  │
│ │ Date: [2026-01-28]       Date: [2026-01-28]       │  │
│ │ Time: [06:30]            Time: [14:45]            │  │
│ │ Lat:  [57.5083]          Lat:  [57.5200]          │  │
│ │ Lon:  [-152.2583]        Lon:  [-152.2700]        │  │
│ │                                                    │  │
│ │ Bottom Depth: [150] fathoms  Sea Depth: [75] fath │  │
│ │ Amount: [42] fish                                  │  │
│ └────────────────────────────────────────────────────┘  │
│                                                         │
│ ┌─ Haul 2 ──────────────────────────────────── [✕] ─┐  │
│ │ ...                                                │  │
│ └────────────────────────────────────────────────────┘  │
│                                                         │
│ [+ Add Haul]                                            │
│                                                         │
│                              [Cancel]  [Create Alert]   │
└─────────────────────────────────────────────────────────┘
```

---

## Testing Considerations

1. **Backwards compatibility**: Existing alerts should display with 1 haul
2. **Multiple hauls**: Create alert with 3+ hauls, verify all save correctly
3. **Coordinate conversion**: Test DMS ↔ decimal conversion accuracy
4. **Email notifications**: Verify haul details appear in shared alert emails
5. **RPCA dropdown**: Verify lookup table populates correctly
6. **Validation**: Test Alaska coordinate bounds on all lat/long fields
7. **Edit flow**: Verify managers can edit haul details after creation

---

## Out of Scope (Deferred)

- VMS data integration (future year)
- RPCA area boundary coordinates/mapping
- Automatic RPCA area detection from coordinates
- Vessel owner mobile optimization

---

## Definition of Done

- [ ] Migration 012 created and tested
- [ ] Coordinate converter utility in `app/utils/`
- [ ] Bycatch alerts page supports multiple hauls
- [ ] RPCA dropdown populated from lookup table
- [ ] Coordinate format toggle works
- [ ] Email notifications include haul details
- [ ] Existing alerts migrated to single haul
- [ ] Transfers page has secondary species + halibut + MT display
- [ ] All existing tests pass
- [ ] New tests for haul CRUD operations
