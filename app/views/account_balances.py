"""Account Balances page - displays latest balance data by co-op and species."""

import streamlit as st
import pandas as pd
from app.config import supabase


def show():
    from app.utils.styles import page_header
    page_header("Account Balances", "Latest balance data by co-op and species")

    # Fetch data from account_balances view
    response = supabase.table("account_balances").select("*").execute()

    if not response.data:
        st.info("No account balance data uploaded yet.")
        return

    df = pd.DataFrame(response.data)

    # Show last uploaded time
    if 'created_at' in df.columns:
        last_upload = pd.to_datetime(df['created_at']).max()
        st.caption(f"Last uploaded: {last_upload.strftime('%B %d, %Y at %I:%M %p')}")

    # Reorder columns for readability
    column_order = [
        "coop_code",
        "species_group",
        "balance_date",
        "initial_quota",
        "transfers_in",
        "transfers_out",
        "total_quota",
        "total_catch",
        "remaining_quota",
        "percent_taken",
        "account_name",
        "source_file",
        "created_at"
    ]

    # Only include columns that exist
    display_cols = [c for c in column_order if c in df.columns]
    df = df[display_cols]

    # Sort by coop_code and species_group
    df = df.sort_values(["coop_code", "species_group"])

    # Display table
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(f"Showing {len(df)} records")
