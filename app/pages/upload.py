"""Upload page - file uploads for eFish data."""

import streamlit as st
import pandas as pd


def show():
    """Display the upload page with two upload sections."""
    st.header("Upload")

    # Section 1: Account Balance
    st.subheader("Account Balance")
    st.caption("Upload coopaccountbalance.csv - Summary snapshot by species")

    balance_file = st.file_uploader("Choose CSV file", type=['csv'], key="balance_upload")

    if balance_file:
        try:
            df = pd.read_csv(balance_file)
            st.write(f"Preview: {len(df)} rows")
            st.dataframe(df, use_container_width=True)

            if st.button("Import Balance Data", key="import_balance"):
                st.info("Import logic coming soon")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.divider()

    # Section 2: Catch Detail
    st.subheader("Catch Detail")
    st.caption("Upload coopaccountdetail.xlsx - Individual harvest records")

    detail_file = st.file_uploader("Choose Excel file", type=['xlsx'], key="detail_upload")

    if detail_file:
        try:
            df = pd.read_excel(detail_file)
            st.write(f"Preview: {len(df)} rows")
            st.dataframe(df, use_container_width=True)

            if st.button("Import Catch Detail", key="import_detail"):
                st.info("Import logic coming soon")
        except Exception as e:
            st.error(f"Error reading file: {e}")
