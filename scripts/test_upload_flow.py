"""
Test script for the complete upload flow.
Run from project root: python scripts/test_upload_flow.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import supabase
from app.utils.parsers import parse_efish, get_harvest_records, ParseError, ValidationError


def main():
    print("Testing Upload Flow...")
    print("=" * 60)

    # 1. Run migration to add status column
    print("\n1. Running migration to add status column...")
    try:
        # Check if status column exists by trying to select it
        test_response = supabase.table("file_uploads").select("status").limit(1).execute()
        print("   Status column already exists.")
    except Exception as e:
        if "status" in str(e).lower():
            print("   Adding status column...")
            # Run the migration SQL
            migration_sql = """
            ALTER TABLE file_uploads
            ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'uploaded';
            """
            try:
                supabase.rpc("exec_sql", {"sql": migration_sql}).execute()
                print("   Status column added successfully.")
            except Exception as e2:
                print(f"   Note: Could not add column via RPC: {e2}")
                print("   You may need to run the migration manually in Supabase SQL Editor.")
        else:
            print(f"   Unexpected error: {e}")

    # 2. Read sample_efish_data.csv
    print("\n2. Reading sample_efish_data.csv...")
    sample_file = Path(__file__).parent.parent / "sample_efish_data.csv"

    if not sample_file.exists():
        print(f"   ERROR: File not found: {sample_file}")
        return

    print(f"   File: {sample_file}")

    # 3. Parse the file
    print("\n3. Parsing file with parse_efish()...")
    try:
        with open(sample_file, "rb") as f:
            parsed_records = parse_efish(f, "sample_efish_data.csv")

        print(f"   SUCCESS! Parsed {len(parsed_records)} records.")

    except ValidationError as e:
        print(f"\n   VALIDATION ERROR:\n{e}")
        return

    except ParseError as e:
        print(f"\n   PARSE ERROR: {e}")
        return

    except Exception as e:
        print(f"\n   UNEXPECTED ERROR: {type(e).__name__}: {e}")
        return

    # 4. Insert records into harvests table
    print("\n4. Inserting records into harvests table...")

    # Extract only harvest table fields
    harvest_records = get_harvest_records(parsed_records)
    print(f"   Prepared {len(harvest_records)} records for insert.")

    # Show first record as example
    if harvest_records:
        print("\n   Example record:")
        for k, v in harvest_records[0].items():
            print(f"     {k}: {v}")

    try:
        # Insert records
        response = supabase.table("harvests").insert(harvest_records).execute()

        if response.data:
            print(f"\n   SUCCESS! Inserted {len(response.data)} harvest records.")
        else:
            print("\n   ERROR: No data returned from insert.")
            return

    except Exception as e:
        error_msg = str(e)
        if "duplicate" in error_msg.lower():
            print(f"\n   WARNING: Some records may already exist (duplicate key).")
            print(f"   Error: {error_msg[:200]}...")
        else:
            print(f"\n   INSERT ERROR: {e}")
        return

    # 5. Verify by querying harvests table
    print("\n5. Verifying harvests table...")
    try:
        count_response = supabase.table("harvests").select("id", count="exact").execute()
        total_count = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
        print(f"   Total records in harvests table: {total_count}")

        # Show recent records
        recent_response = supabase.table("harvests").select("*").order("created_at", desc=True).limit(3).execute()
        if recent_response.data:
            print("\n   Most recent harvests:")
            for i, rec in enumerate(recent_response.data):
                print(f"\n   Record {i+1}:")
                print(f"     ID: {rec['id'][:8]}...")
                print(f"     Landed Date: {rec.get('landed_date')}")
                print(f"     Amount: {rec.get('amount')} lbs")
                print(f"     Vessel ID: {rec.get('vessel_id', 'N/A')[:8]}...")
                print(f"     Species ID: {rec.get('species_id', 'N/A')[:8]}...")

    except Exception as e:
        print(f"   Error verifying: {e}")

    print("\n" + "=" * 60)
    print("Upload flow test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
