"""
Insert test data into Supabase for development and testing.
Run from project root: python scripts/insert_test_data.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import supabase


def main():
    print("Inserting test data into Supabase...\n")

    try:
        # 1. Insert Cooperatives
        print("1. Inserting cooperatives...")
        cooperatives = [
            {"cooperative_name": "Rockfish Co-op Alpha", "contact_info": "alpha@rockfish.example.com"},
            {"cooperative_name": "Rockfish Co-op Beta", "contact_info": "beta@rockfish.example.com"},
        ]
        coop_response = supabase.table("cooperatives").insert(cooperatives).execute()
        coop_data = coop_response.data
        print(f"   Inserted {len(coop_data)} cooperatives")

        # Map cooperative names to IDs
        coop_ids = {c["cooperative_name"]: c["id"] for c in coop_data}
        alpha_id = coop_ids["Rockfish Co-op Alpha"]
        beta_id = coop_ids["Rockfish Co-op Beta"]

        # 2. Insert Members
        print("2. Inserting members...")
        members = [
            {"member_name": "John Smith", "contact_info": "john.smith@example.com"},
            {"member_name": "Jane Doe", "contact_info": "jane.doe@example.com"},
            {"member_name": "Bob Johnson", "contact_info": "bob.johnson@example.com"},
            {"member_name": "Sarah Wilson", "contact_info": "sarah.wilson@example.com"},
        ]
        member_response = supabase.table("members").insert(members).execute()
        member_data = member_response.data
        print(f"   Inserted {len(member_data)} members")

        # Map member names to IDs
        member_ids = {m["member_name"]: m["id"] for m in member_data}

        # 3. Insert Vessels
        print("3. Inserting vessels...")
        vessels = [
            {
                "vessel_name": "F/V Northern Light",
                "vessel_id_number": "AK-001-NL",
                "member_id": member_ids["John Smith"],
            },
            {
                "vessel_name": "F/V Sea Spray",
                "vessel_id_number": "AK-002-SS",
                "member_id": member_ids["Jane Doe"],
            },
            {
                "vessel_name": "F/V Pacific Star",
                "vessel_id_number": "AK-003-PS",
                "member_id": member_ids["Bob Johnson"],
            },
            {
                "vessel_name": "F/V Ocean Quest",
                "vessel_id_number": "AK-004-OQ",
                "member_id": member_ids["Sarah Wilson"],
            },
        ]
        vessel_response = supabase.table("vessels").insert(vessels).execute()
        vessel_data = vessel_response.data
        print(f"   Inserted {len(vessel_data)} vessels")

        # Map vessel names to IDs
        vessel_ids = {v["vessel_name"]: v["id"] for v in vessel_data}

        # 4. Insert Cooperative Memberships
        print("4. Inserting cooperative memberships...")
        memberships = [
            # Alpha co-op members
            {
                "member_id": member_ids["John Smith"],
                "cooperative_id": alpha_id,
                "effective_from": "2025-01-01",
                "effective_to": None,
            },
            {
                "member_id": member_ids["Jane Doe"],
                "cooperative_id": alpha_id,
                "effective_from": "2025-01-01",
                "effective_to": None,
            },
            # Beta co-op members
            {
                "member_id": member_ids["Bob Johnson"],
                "cooperative_id": beta_id,
                "effective_from": "2025-01-01",
                "effective_to": None,
            },
            {
                "member_id": member_ids["Sarah Wilson"],
                "cooperative_id": beta_id,
                "effective_from": "2025-01-01",
                "effective_to": None,
            },
        ]
        membership_response = supabase.table("cooperative_memberships").insert(memberships).execute()
        print(f"   Inserted {len(membership_response.data)} cooperative memberships")

        # 5. Insert Vessel Cooperative Assignments
        print("5. Inserting vessel cooperative assignments...")
        assignments = [
            # Alpha co-op vessels
            {
                "vessel_id": vessel_ids["F/V Northern Light"],
                "cooperative_id": alpha_id,
                "effective_from": "2025-01-01",
                "effective_to": None,
            },
            {
                "vessel_id": vessel_ids["F/V Sea Spray"],
                "cooperative_id": alpha_id,
                "effective_from": "2025-01-01",
                "effective_to": None,
            },
            # Beta co-op vessels
            {
                "vessel_id": vessel_ids["F/V Pacific Star"],
                "cooperative_id": beta_id,
                "effective_from": "2025-01-01",
                "effective_to": None,
            },
            {
                "vessel_id": vessel_ids["F/V Ocean Quest"],
                "cooperative_id": beta_id,
                "effective_from": "2025-01-01",
                "effective_to": None,
            },
        ]
        assignment_response = supabase.table("vessel_cooperative_assignments").insert(assignments).execute()
        print(f"   Inserted {len(assignment_response.data)} vessel assignments")

        print("\n" + "=" * 50)
        print("Test data inserted successfully!")
        print("=" * 50)
        print("\nSummary:")
        print(f"  - Cooperatives: {len(coop_data)}")
        print(f"  - Members: {len(member_data)}")
        print(f"  - Vessels: {len(vessel_data)}")
        print(f"  - Cooperative Memberships: {len(membership_response.data)}")
        print(f"  - Vessel Assignments: {len(assignment_response.data)}")

    except Exception as e:
        print(f"\nError inserting test data: {e}")
        print("\nNote: If you see duplicate key errors, the test data may already exist.")
        print("You can clear the tables in Supabase and run this script again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
