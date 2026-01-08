"""Account Detail page - displays catch activity records by vessel."""

import streamlit as st
import pandas as pd
from app.config import supabase


def show():
    st.header("Account Detail")
    st.caption("Catch activity records by vessel")

    # Fetch data from account_detail view
    response = supabase.table("account_detail").select("*").execute()

    if not response.data:
        st.info("No account detail data uploaded yet.")
        return

    df = pd.DataFrame(response.data)

    # Show last uploaded time
    if 'created_at' in df.columns:
        last_upload = pd.to_datetime(df['created_at']).max()
        st.caption(f"Last uploaded: {last_upload.strftime('%B %d, %Y at %I:%M %p')}")

    # Reorder columns for readability
    column_order = [
        "catch_activity_date",
        "vessel_name",
        "adfg",
        "species_name",
        "species_code",
        "weight_posted",
        "processor_permit",
        "landing_date",
        "report_number",
        "gear_code",
        "reporting_area",
        "source_file",
        "created_at"
    ]

    # Only include columns that exist
    display_cols = [c for c in column_order if c in df.columns]
    df = df[display_cols]

    # Sort by catch_activity_date descending (most recent first)
    df = df.sort_values("catch_activity_date", ascending=False)

    # Display table
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(f"Showing {len(df)} records")
