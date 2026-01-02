"""
Insert test quota allocations for 2025 season.
Run from project root: python scripts/insert_test_quotas.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import supabase


def main():
    print("Inserting test quota allocations for 2025...")
    print("=" * 60)

    # 1. Fetch 2025 season
    print("\n1. Fetching 2025 season...")
    season_response = supabase.table("seasons").select("id, year").eq("year", 2025).execute()
    if not season_response.data:
        print("   ERROR: 2025 season not found. Please add it first.")
        return
    season_id = season_response.data[0]["id"]
    print(f"   Found season: {season_id[:8]}...")

    # 2. Fetch cooperatives
    print("\n2. Fetching cooperatives...")
    coop_response = supabase.table("cooperatives").select("id, cooperative_name").execute()
    if not coop_response.data:
        print("   ERROR: No cooperatives found.")
        return
    coops = {c["cooperative_name"]: c["id"] for c in coop_response.data}
    print(f"   Found {len(coops)} cooperatives")

    alpha_id = coops.get("Rockfish Co-op Alpha")
    beta_id = coops.get("Rockfish Co-op Beta")

    if not alpha_id or not beta_id:
        print("   ERROR: Could not find Alpha or Beta cooperatives")
        print(f"   Available: {list(coops.keys())}")
        return

    # 3. Fetch species
    print("\n3. Fetching species...")
    species_response = supabase.table("species").select("id, species_name, species_code").execute()
    if not species_response.data:
        print("   ERROR: No species found.")
        return
    species = {s["species_name"]: s["id"] for s in species_response.data}
    print(f"   Found {len(species)} species")

    pop_id = species.get("Pacific Ocean Perch")
    dusky_id = species.get("Dusky Rockfish")
    northern_id = species.get("Northern Rockfish")

    if not all([pop_id, dusky_id, northern_id]):
        print("   ERROR: Could not find all required species")
        print(f"   Available: {list(species.keys())}")
        return

    # 4. Define quota allocations
    quotas = [
        # Rockfish Co-op Alpha
        {"season_id": season_id, "cooperative_id": alpha_id, "species_id": pop_id, "amount": 150000},
        {"season_id": season_id, "cooperative_id": alpha_id, "species_id": dusky_id, "amount": 80000},
        {"season_id": season_id, "cooperative_id": alpha_id, "species_id": northern_id, "amount": 40000},
        # Rockfish Co-op Beta
        {"season_id": season_id, "cooperative_id": beta_id, "species_id": pop_id, "amount": 120000},
        {"season_id": season_id, "cooperative_id": beta_id, "species_id": dusky_id, "amount": 60000},
        {"season_id": season_id, "cooperative_id": beta_id, "species_id": northern_id, "amount": 30000},
    ]

    # 5. Insert quotas
    print("\n4. Inserting quota allocations...")
    try:
        response = supabase.table("quota_allocations").insert(quotas).execute()
        if response.data:
            print(f"   Inserted {len(response.data)} quota allocations")
        else:
            print("   ERROR: No data returned from insert")
            return
    except Exception as e:
        print(f"   ERROR: {e}")
        return

    # 6. Verify and summarize
    print("\n5. Verifying quota allocations...")
    verify_response = supabase.table("quota_allocations").select("*").eq("season_id", season_id).execute()

    if verify_response.data:
        print(f"   Total allocations for 2025: {len(verify_response.data)}")

        # Summarize by cooperative
        print("\n" + "=" * 60)
        print("Summary:")
        print("=" * 60)

        # Get names for display
        species_names = {s["id"]: s["species_name"] for s in species_response.data}
        coop_names = {c["id"]: c["cooperative_name"] for c in coop_response.data}

        for coop_id, coop_name in [(alpha_id, "Rockfish Co-op Alpha"), (beta_id, "Rockfish Co-op Beta")]:
            print(f"\n{coop_name}:")
            coop_quotas = [q for q in verify_response.data if q["cooperative_id"] == coop_id]
            total = 0
            for q in coop_quotas:
                species_name = species_names.get(q["species_id"], "Unknown")
                amount = q["amount"]
                total += amount
                print(f"  - {species_name}: {amount:,.0f} lbs")
            print(f"  Total: {total:,.0f} lbs")

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
