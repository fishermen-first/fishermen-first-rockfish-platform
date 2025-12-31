"""
Test script for eFish parser.
Run from project root: python scripts/test_parser.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.parsers import (
    parse_efish,
    fetch_vessels_lookup,
    fetch_species_lookup,
    fetch_processors_lookup,
    fetch_seasons_lookup,
    ParseError,
    ValidationError,
)


def main():
    print("Testing eFish Parser...")
    print("=" * 60)

    # Show available lookups
    print("\n1. Checking lookup tables...")

    vessels = fetch_vessels_lookup()
    print(f"\n   Vessels ({len(vessels)}):")
    if vessels:
        for vid, uuid in vessels.items():
            print(f"     '{vid}' -> {uuid[:8]}...")
    else:
        print("     (none found)")

    species = fetch_species_lookup()
    print(f"\n   Species ({len(species)}):")
    if species:
        for code, uuid in species.items():
            print(f"     '{code}' -> {uuid[:8]}...")
    else:
        print("     (none found)")

    processors = fetch_processors_lookup()
    print(f"\n   Processors ({len(processors)}):")
    if processors:
        for name, uuid in processors.items():
            print(f"     '{name}' -> {uuid[:8]}...")
    else:
        print("     (none found)")

    seasons = fetch_seasons_lookup()
    print(f"\n   Seasons ({len(seasons)}):")
    if seasons:
        for year, uuid in seasons.items():
            print(f"     {year} -> {uuid[:8]}...")
    else:
        print("     (none found)")

    # Try to parse the sample file
    print("\n" + "=" * 60)
    print("\n2. Parsing sample_efish_data.csv...")

    sample_file = Path(__file__).parent.parent / "sample_efish_data.csv"

    if not sample_file.exists():
        print(f"   ERROR: File not found: {sample_file}")
        return

    print(f"   File: {sample_file}")

    try:
        with open(sample_file, "rb") as f:
            records = parse_efish(f, "sample_efish_data.csv")

        print(f"\n   SUCCESS! Parsed {len(records)} records.")
        print("\n   First 3 records:")
        for i, rec in enumerate(records[:3]):
            print(f"\n   Record {i+1}:")
            for k, v in rec.items():
                print(f"     {k}: {v}")

    except ValidationError as e:
        print(f"\n   VALIDATION ERROR:\n{e}")

    except ParseError as e:
        print(f"\n   PARSE ERROR: {e}")

    except Exception as e:
        print(f"\n   UNEXPECTED ERROR: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print("\nNOTE: If lookups failed, you may need to:")
    print("  1. Add species with codes: 141, 137, 193")
    print("  2. Add processors: 'Kodiak Seafoods', 'Westward Seafoods'")
    print("  3. Add a 2025 season")
    print("  4. Update vessel IDs to match: ADF&G-001, ADF&G-002, etc.")
    print("     (or update sample file to use: AK-001-NL, AK-002-SS, etc.)")


if __name__ == "__main__":
    main()
