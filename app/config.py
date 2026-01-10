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
