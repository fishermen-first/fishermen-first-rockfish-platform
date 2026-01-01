"""
Test script to verify harvests table data and FK relationships.
Run from project root: python scripts/test_harvests.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import supabase


def main():
    print("Testing Harvests Table...")
    print("=" * 60)

    # 1. Query harvests table
    print("\n1. Querying harvests table...")
    try:
        response = supabase.table("harvests").select("*").execute()
        harvests = response.data or []
        print(f"   Total records: {len(harvests)}")
    except Exception as e:
        print(f"   Error: {e}")
        return

    if not harvests:
        print("\n   No harvest records found.")
        return

    # 2. Fetch related tables for joins
    print("\n2. Fetching related tables...")

    # Vessels
    vessels_response = supabase.table("vessels").select("id, vessel_name").execute()
    vessels = {v["id"]: v["vessel_name"] for v in vessels_response.data} if vessels_response.data else {}
    print(f"   Vessels: {len(vessels)}")

    # Species
    species_response = supabase.table("species").select("id, species_name, species_code").execute()
    species = {s["id"]: s for s in species_response.data} if species_response.data else {}
    print(f"   Species: {len(species)}")

    # Processors
    processors_response = supabase.table("processors").select("id, processor_name").execute()
    processors = {p["id"]: p["processor_name"] for p in processors_response.data} if processors_response.data else {}
    print(f"   Processors: {len(processors)}")

    # Seasons
    seasons_response = supabase.table("seasons").select("id, year").execute()
    seasons = {s["id"]: s["year"] for s in seasons_response.data} if seasons_response.data else {}
    print(f"   Seasons: {len(seasons)}")

    # 3. Summary statistics
    print("\n3. Summary Statistics")
    print("-" * 40)

    # Date range
    dates = [h["landed_date"] for h in harvests if h.get("landed_date")]
    if dates:
        print(f"   Date range: {min(dates)} to {max(dates)}")
    else:
        print("   Date range: No dates found")

    # Total amount
    total_lbs = sum(h.get("amount", 0) or 0 for h in harvests)
    print(f"   Total harvest: {total_lbs:,.0f} lbs")

    # Records by species
    print("\n   By Species:")
    species_counts = {}
    species_amounts = {}
    for h in harvests:
        sid = h.get("species_id")
        species_name = species.get(sid, {}).get("species_name", "Unknown") if sid else "Unknown"
        species_counts[species_name] = species_counts.get(species_name, 0) + 1
        species_amounts[species_name] = species_amounts.get(species_name, 0) + (h.get("amount", 0) or 0)

    for name in sorted(species_counts.keys()):
        print(f"     {name}: {species_counts[name]} records, {species_amounts[name]:,.0f} lbs")

    # Records by vessel
    print("\n   By Vessel:")
    vessel_counts = {}
    vessel_amounts = {}
    for h in harvests:
        vid = h.get("vessel_id")
        vessel_name = vessels.get(vid, "Unknown") if vid else "Unknown"
        vessel_counts[vessel_name] = vessel_counts.get(vessel_name, 0) + 1
        vessel_amounts[vessel_name] = vessel_amounts.get(vessel_name, 0) + (h.get("amount", 0) or 0)

    for name in sorted(vessel_counts.keys()):
        print(f"     {name}: {vessel_counts[name]} records, {vessel_amounts[name]:,.0f} lbs")

    # Records by processor
    print("\n   By Processor:")
    processor_counts = {}
    for h in harvests:
        pid = h.get("processor_id")
        processor_name = processors.get(pid, "Unknown") if pid else "N/A"
        processor_counts[processor_name] = processor_counts.get(processor_name, 0) + 1

    for name in sorted(processor_counts.keys()):
        print(f"     {name}: {processor_counts[name]} records")

    # 4. Check for missing FK relationships
    print("\n4. Checking FK Relationships...")
    print("-" * 40)

    missing_vessel = [h for h in harvests if not h.get("vessel_id") or h["vessel_id"] not in vessels]
    missing_species = [h for h in harvests if not h.get("species_id") or h["species_id"] not in species]
    missing_processor = [h for h in harvests if h.get("processor_id") and h["processor_id"] not in processors]
    missing_season = [h for h in harvests if not h.get("season_id") or h["season_id"] not in seasons]

    print(f"   Missing/invalid vessel_id: {len(missing_vessel)}")
    print(f"   Missing/invalid species_id: {len(missing_species)}")
    print(f"   Missing/invalid processor_id: {len(missing_processor)}")
    print(f"   Missing/invalid season_id: {len(missing_season)}")

    if missing_vessel:
        print("\n   Records with missing vessel:")
        for h in missing_vessel[:5]:
            print(f"     ID: {h['id'][:8]}..., vessel_id: {h.get('vessel_id', 'NULL')}")

    if missing_species:
        print("\n   Records with missing species:")
        for h in missing_species[:5]:
            print(f"     ID: {h['id'][:8]}..., species_id: {h.get('species_id', 'NULL')}")

    if missing_processor:
        print("\n   Records with invalid processor:")
        for h in missing_processor[:5]:
            print(f"     ID: {h['id'][:8]}..., processor_id: {h.get('processor_id', 'NULL')}")

    if missing_season:
        print("\n   Records with missing season:")
        for h in missing_season[:5]:
            print(f"     ID: {h['id'][:8]}..., season_id: {h.get('season_id', 'NULL')}")

    # 5. Sample records
    print("\n5. Sample Records (first 3)")
    print("-" * 40)
    for i, h in enumerate(harvests[:3]):
        vessel_name = vessels.get(h.get("vessel_id"), "Unknown")
        species_info = species.get(h.get("species_id"), {})
        species_name = species_info.get("species_name", "Unknown")
        processor_name = processors.get(h.get("processor_id"), "N/A")

        print(f"\n   Record {i+1}:")
        print(f"     Date: {h.get('landed_date')}")
        print(f"     Vessel: {vessel_name}")
        print(f"     Species: {species_name}")
        print(f"     Amount: {h.get('amount', 0):,.0f} lbs")
        print(f"     Processor: {processor_name}")

    print("\n" + "=" * 60)
    print("Test complete!")


if __name__ == "__main__":
    main()
