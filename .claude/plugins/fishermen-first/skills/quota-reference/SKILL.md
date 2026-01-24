---
name: Quota Reference
description: This skill should be used when the user asks about "quota calculation", "quota remaining", "species codes", "coordinate format", "GPS coordinates", "degrees minutes", "DMS format", "transfer rules", "PSC species", "Alaska waters", "validation rules", or needs domain-specific fisheries business logic for the Central GOA Rockfish Program.
version: 0.1.0
---

# Quota Reference

Domain-specific knowledge for the Fishermen First Central GOA Rockfish Program, including quota calculations, species codes, coordinate formats, and validation rules.

## Quota Calculation

### Quota Remaining Formula

```
Quota Remaining = Allocation + Transfers In - Transfers Out - Harvested
```

### Database View

The `quota_remaining` view calculates this automatically:

```sql
SELECT
    llp,
    species_code,
    year,
    allocation,
    transfers_in,
    transfers_out,
    harvested,
    (allocation + transfers_in - transfers_out - harvested) AS remaining_lbs
FROM quota_summary
```

## Species Codes

### Primary Species (Rockfish)

| Species | Code | Unit | Description |
|---------|------|------|-------------|
| POP | 141 | lbs | Pacific Ocean Perch |
| NR | 136 | lbs | Northern Rockfish |
| Dusky | 172 | lbs | Dusky Rockfish |

### PSC Species (Prohibited Species Catch)

| Species | Code | Unit | Description |
|---------|------|------|-------------|
| Halibut | TBD | lbs | Pacific Halibut |
| Salmon | TBD | count | Chinook Salmon (counted, not weighed) |

### Secondary Species

| Species | Unit |
|---------|------|
| Sablefish | lbs |
| Pacific Cod | lbs |
| Thornyhead | lbs |

## GPS Coordinates

### Captain Format (DMS)

Captains report coordinates in degrees-minutes-seconds format:

```
57° 30' 00" N, 152° 15' 30" W
```

Or degrees-minutes (decimal minutes):

```
57° 30.5' N, 152° 15.5' W
```

### Database Format (Decimal)

Database stores decimal degrees:

```
latitude: 57.5000
longitude: -152.2583
```

### Conversion Functions

**DMS to Decimal:**

```python
def dms_to_decimal(degrees: int, minutes: float, direction: str) -> float:
    """Convert degrees-minutes to decimal degrees."""
    decimal = degrees + (minutes / 60)
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal

# Example: 57° 30.5' N -> 57.5083
dms_to_decimal(57, 30.5, 'N')  # Returns 57.5083

# Example: 152° 15.5' W -> -152.2583
dms_to_decimal(152, 15.5, 'W')  # Returns -152.2583
```

**Decimal to DMS:**

```python
def decimal_to_dms(decimal: float, is_latitude: bool) -> str:
    """Convert decimal degrees to DMS string."""
    direction = ''
    if is_latitude:
        direction = 'N' if decimal >= 0 else 'S'
    else:
        direction = 'W' if decimal < 0 else 'E'

    decimal = abs(decimal)
    degrees = int(decimal)
    minutes = (decimal - degrees) * 60

    return f"{degrees}° {minutes:.1f}' {direction}"

# Example: 57.5083 -> "57° 30.5' N"
decimal_to_dms(57.5083, is_latitude=True)

# Example: -152.2583 -> "152° 15.5' W"
decimal_to_dms(-152.2583, is_latitude=False)
```

### UI Input Pattern

For Streamlit forms, use separate inputs for degrees and minutes:

```python
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    lat_deg = st.number_input("Lat Degrees", 50, 72, 57)
with col2:
    lat_min = st.number_input("Lat Minutes", 0.0, 59.99, 0.0, step=0.1)
with col3:
    st.write("")  # Spacer
    st.write("N")  # Alaska is always North

# Convert for storage
latitude = dms_to_decimal(lat_deg, lat_min, 'N')
```

## Alaska Waters Bounds

### Valid Coordinate Ranges

| Coordinate | Min | Max | Notes |
|------------|-----|-----|-------|
| Latitude | 50.0° | 72.0° | Always North (positive) |
| Longitude | -180.0° | -130.0° | Always West (negative) |

### Central GOA Typical Range

| Coordinate | Typical Range |
|------------|---------------|
| Latitude | 56° - 60° N |
| Longitude | 145° - 160° W |

### Default Values (Kodiak Area)

```python
DEFAULT_LATITUDE = 57.0   # 57° 00' N
DEFAULT_LONGITUDE = -152.0  # 152° 00' W
```

## Transfer Validation Rules

### Business Rules

1. **Same vessel blocked**: Cannot transfer to same LLP
2. **Sufficient quota**: Cannot transfer more than available
3. **Positive amount**: Amount must be > 0
4. **Valid species**: Must be primary species (141, 136, 172)
5. **Current year**: Transfers only for current fishing year

### Validation Function

```python
def validate_transfer(from_llp, to_llp, species_code, amount, available) -> tuple[bool, list[str]]:
    """Validate quota transfer."""
    errors = []

    if from_llp == to_llp:
        errors.append("Cannot transfer quota to the same vessel.")

    if amount <= 0:
        errors.append("Transfer amount must be greater than zero.")

    if amount > available:
        errors.append(f"Amount exceeds available quota ({available:,.0f} lbs).")

    if species_code not in [141, 136, 172]:
        errors.append("Invalid species for transfer.")

    return len(errors) == 0, errors
```

## Bycatch Alert Validation

### Required Fields

- Reporting vessel (LLP)
- Species (PSC only: Halibut or Salmon)
- Location (lat/lon in Alaska waters)
- Amount (lbs for Halibut, count for Salmon)

### Coordinate Validation

```python
def validate_alaska_coordinates(lat: float, lon: float) -> tuple[bool, str | None]:
    """Validate coordinates are in Alaska fishing waters."""
    if lat < 50.0 or lat > 72.0:
        return False, "Latitude must be between 50° and 72° N"
    if lon < -180.0 or lon > -130.0:
        return False, "Longitude must be between 130° and 180° W"
    return True, None
```

## Additional Resources

### Reference Files

- **`references/species-details.md`** - Complete species information
- **`references/coordinate-utils.md`** - Coordinate conversion utilities

### Scripts

- **`scripts/coordinate_converter.py`** - Python module for DMS/decimal conversion
