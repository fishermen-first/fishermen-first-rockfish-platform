import os
from dotenv import load_dotenv
from supabase import create_client, Client
import streamlit as st

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")


@st.cache_resource
def get_supabase_client() -> Client:
    """Create and cache the Supabase client connection."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase: Client = get_supabase_client()

# =============================================================================
# APPLICATION CONSTANTS
# =============================================================================

# Current fishing season year
CURRENT_YEAR = 2026

# Metric ton conversion factor (for e-fish reconciliation)
# 1 metric ton = 2,204.62 pounds
LBS_PER_MT = 2204.62
