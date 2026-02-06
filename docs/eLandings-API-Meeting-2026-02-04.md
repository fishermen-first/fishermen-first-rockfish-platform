# eLandings API Meeting Prep

**Date:** Tuesday, February 4, 2026
**Purpose:** Discuss API access to Electronic Groundfish Ticket data for Central GOA Rockfish Program

---

## What We Need

**Data Source:** Electronic Groundfish Ticket (same structure as attached pollock example)
**Management Program:** Central GOA Rockfish (not OA/pollock)
**NOT needed:** Production reports

---

## Fields We Need from the Fish Ticket

### Header/Vessel Identification
| Field | Example | Our Use |
|-------|---------|---------|
| ADF&G NO. | (vessel number) | Vessel identification |
| Permit | (CFEC/LLP) | **Primary key** - links to our `coop_members.llp` |
| Vessel Name | | Display name |
| Mgmt Pgm + ID | "OA" / Rockfish code | Filter for Central GOA Rockfish only |

### Trip/Landing Info
| Field | Example | Our Use |
|-------|---------|---------|
| Date Landed | 02/09/2023 | Landing date for harvest records |
| Date Fishing Began | 02/07/2023 | Optional - trip tracking |
| Days Fished | 1 | Optional |
| Port of Landing | KOD Kodiak | Optional - reporting |
| Custom Processor | | Maps to our `processors` table |

### Catch Detail (per species line item)
| Field | Example | Our Use |
|-------|---------|---------|
| SPECIES | 141 POP, 136 NR, 172 Dusky | **Critical** - species code |
| STAT AREA | 01 | Statistical area |
| DEL. COND | Whole | Delivery condition |
| SCALE WEIGHT | 2,280 | Weight at scale |
| DISP. | 60 Sold, 98 Disc atsea | Disposition code |

### Round Weights (Bottom of Ticket)
| Field | Example | Our Use |
|-------|---------|---------|
| **Round Weight by Species** | POP Round Weight: 2,280 | **This is what we need for quota tracking** |
| Total Round Weight | 269,426 | Verification |

### Identifiers
| Field | Our Use |
|-------|---------|
| Landing Report ID | Unique record identifier (deduplication) |
| CFEC Serial Number | Cross-reference |

---

## Questions for eLandings Team

### 1. Authentication & Access
- [ ] What authentication method? (OAuth, API keys, certificates?)
- [ ] How do we get API credentials?
- [ ] Is there a sandbox/test environment?
- [ ] Any IP whitelisting required?
- [ ] What are the rate limits on requests?

### 2. Query Parameters
- [ ] Can we query by **vessel**?
- [ ] Can we query by **permit holder** (LLP)?
- [ ] Can we query by **date range**?
- [ ] Can we query by **Landing Report ID**?
- [ ] Can we filter by **Management Program**? (Central GOA Rockfish only)
- [ ] What are all the available query parameters?

### 3. Data Structure
- [ ] **Line item granularity** - Does the API return catch data as nested objects per landing, or are there separate endpoints?
- [ ] What's the response format? (JSON, XML?)
- [ ] Is there pagination for large result sets?

### 4. Data Freshness & History
- [ ] **Real-time vs. batch** - What's the latency between landing submission and API availability?
- [ ] **Historical data** - How far back can we pull?
- [ ] **Webhook/push options** - Can we subscribe to new landings for specific permits/vessels?

### 5. Data Specifics
- [ ] Do you provide **round weights** via API? (critical for quota tracking)
- [ ] Are species codes standardized? (we use: 141=POP, 136=NR, 172=Dusky)
- [ ] **Disposition/discard data** - Is discard information (like salmon shark discards) included, or is that a separate report?
- [ ] **Price/financial data** - Is sold weight, price, and amount available via API, or restricted?
- [ ] How are **partial deliveries** handled?
- [ ] How are **amended/corrected tickets** handled? (updates vs new records?)

### 6. Documentation & Support
- [ ] Is there API documentation we can review?
- [ ] Is there a schema/data dictionary?
- [ ] Who do we contact for technical support?

---

## Our Current System

For context to share with eLandings team:

- **Platform:** Fishermen First - quota tracking for Alaska fishing cooperatives
- **Database:** PostgreSQL (Supabase)
- **Current harvest tracking:** Manual CSV upload from eFish reports
- **Goal:** Automated API sync to replace manual uploads
- **Key table:** `harvests` (llp, species_code, pounds, landing_date, processor_code)

### Species We Track
| Code | Name | Type |
|------|------|------|
| 141 | Pacific Ocean Perch (POP) | Target |
| 136 | Northern Rockfish (NR) | Target |
| 172 | Dusky Rockfish | Target |
| 200 | Halibut | PSC (bycatch) |

---

## Mapping: Fish Ticket to Our Schema

```
Fish Ticket Field        →  Our harvests Table
─────────────────────────────────────────────────
Permit (LLP)             →  llp
SPECIES code             →  species_code
Round Weight             →  pounds
Date Landed              →  landing_date
Custom Processor         →  processor_code
Landing Report ID        →  external_id (for dedup)
```

---

## Follow-up Items

After the meeting, we'll need:
- [ ] API credentials (or process to obtain them)
- [ ] API documentation
- [ ] Test environment access
- [ ] Sample API responses
- [ ] Confidentiality agreement signed (draft exists: `_elandings Confidentiality Agreement_Draft.docx`)

---

## Notes from Meeting

*(To be filled in during/after meeting)*

