import sys
sys.path.insert(0, str(__file__).rsplit("scripts", 1)[0])

from app.config import supabase

try:
    response = supabase.table("cooperatives").select("*").limit(1).execute()
    print("Connection successful")
except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)
