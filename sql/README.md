# Database Schema

## Organization
Rockfish org ID: `06da23e7-4cce-446a-a9f7-67fc86094b98`

## Tables Overview

### Reference Tables
| Table | Purpose | Key Field |
|-------|---------|-----------|
| cooperatives | 4 co-ops (SBS, NP, OBSI, SOK) | coop_code |
| coop_members | 46 LLPs with vessel info | llp |
| vessels | Vessel details | adfg_number |
| processors | 4 processors | processor_code |
| species | 10 species | code |
| annual_tac | TAC by species/year | species_code, year |
| vessel_allocations | Starting quota | llp, species_code, year |
| psc_allocations | PSC limits | species_code, year |
| user_profiles | Auth & roles | user_id, email |

### Transaction Tables (affect quota)
| Table | Purpose | Soft Delete |
|-------|---------|-------------|
| quota_transfers | Transfers between LLPs | is_deleted |
| harvests | From eLandings API | is_deleted |

### Reconciliation Tables (do NOT affect quota)
| Table | Purpose |
|-------|---------|
| account_balances_raw | eFish CSV uploads |
| account_detail_raw | eFish CSV uploads |

### Views
| View | Purpose |
|------|---------|
| quota_remaining | Calculates: allocation + transfers_in - transfers_out - harvested |
| account_balances | Latest balance per coop/species with coop_code mapping |
| account_detail | Raw detail with species_code mapping |

## Species Codes
| Code | Name | Abbrev |
|------|------|--------|
| 141 | Pacific Ocean Perch | POP |
| 136 | Northern Rockfish | NR |
| 172 | Dusky Rockfish | Dusky |
| 200 | Halibut | HLBT |
| 110 | Pacific Cod | PCOD |
| 710 | Sablefish | SABL |
| 143 | Thornyhead | THDS |

## Common Queries

### Get quota remaining for an LLP
```sql
SELECT * FROM quota_remaining
WHERE llp = 'LLP1234' AND year = 2026;
```

### Get all transfers for a species this year
```sql
SELECT * FROM quota_transfers
WHERE species_code = 141
  AND year = 2026
  AND is_deleted = FALSE
ORDER BY transfer_date DESC;
```

### Get co-op totals
```sql
SELECT
    cm.coop_code,
    qr.species_code,
    SUM(qr.allocation_lbs) as total_allocation,
    SUM(qr.remaining_lbs) as total_remaining
FROM quota_remaining qr
JOIN coop_members cm ON qr.llp = cm.llp
WHERE qr.year = 2026
GROUP BY cm.coop_code, qr.species_code;
```

## Schema Files
- `schema.sql` - Original single-tenant schema
- `schema-v2-multi-tenant.sql` - Multi-tenant with org_id + RLS
