"""
Test script for Supabase Storage uploads.
Run from project root: python scripts/test_storage.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import supabase


def main():
    print("Testing Supabase Storage...")
    print("=" * 50)

    # Debug: Check connection
    print("\n1. Checking Supabase connection...")
    print(f"   Supabase client type: {type(supabase)}")
    print(f"   Storage client type: {type(supabase.storage)}")

    # List all buckets with full debug
    print("\n2. Listing all buckets (raw response)...")
    try:
        buckets_response = supabase.storage.list_buckets()
        print(f"   Response type: {type(buckets_response)}")
        print(f"   Response value: {buckets_response}")

        if buckets_response:
            print(f"\n   Found {len(buckets_response)} bucket(s):")
            for i, b in enumerate(buckets_response):
                print(f"   [{i}] Type: {type(b)}")
                print(f"       Raw: {b}")
                if hasattr(b, 'name'):
                    print(f"       Name: {b.name}")
                if hasattr(b, 'id'):
                    print(f"       ID: {b.id}")
                if hasattr(b, 'public'):
                    print(f"       Public: {b.public}")
                if isinstance(b, dict):
                    print(f"       Dict keys: {b.keys()}")
        else:
            print("   No buckets returned (empty response)")

    except Exception as e:
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # Try direct upload to 'uploads' bucket
    print("\n3. Attempting upload to 'uploads' bucket...")
    test_content = b"Test file content from test_storage.py"
    test_path = "test/test_file.txt"

    try:
        response = supabase.storage.from_("uploads").upload(
            path=test_path,
            file=test_content,
            file_options={"content-type": "text/plain"}
        )
        print(f"   Response type: {type(response)}")
        print(f"   Response: {response}")
        print("   SUCCESS!")

        # Cleanup
        print("\n4. Cleaning up test file...")
        del_response = supabase.storage.from_("uploads").remove([test_path])
        print(f"   Delete response: {del_response}")
        print("   SUCCESS!")

    except Exception as e:
        print(f"   Error: {type(e).__name__}: {e}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
