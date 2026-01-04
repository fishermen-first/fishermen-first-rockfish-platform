"""Upload page - simple file upload for eFish data."""

import streamlit as st
import pandas as pd
from datetime import datetime
from app.config import supabase


def show():
    """Display the upload page."""
    st.title("Upload eFish Data")

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose an eFish CSV file",
        type=["csv"],
        help="Upload a CSV file exported from eFish"
    )

    if uploaded_file is not None:
        try:
            # Read the CSV
            df = pd.read_csv(uploaded_file)

            st.subheader("Preview")
            st.dataframe(df.head(10), use_container_width=True, hide_index=True)
            st.caption(f"{len(df)} rows, {len(df.columns)} columns")

            # Show column names
            with st.expander("Column names"):
                st.write(list(df.columns))

            # Upload button
            if st.button("Upload to Database", type="primary"):
                with st.spinner("Uploading..."):
                    success, message = save_upload(uploaded_file, df)

                if success:
                    st.success(message)
                else:
                    st.error(message)

        except Exception as e:
            st.error(f"Error reading file: {e}")


def save_upload(uploaded_file, df: pd.DataFrame) -> tuple[bool, str]:
    """Save the uploaded file metadata to the database."""
    try:
        # Get current user from session
        user_id = st.session_state.get("user_id")
        if not user_id:
            return False, "No user logged in"

        # Create file upload record
        record = {
            "uploaded_by": user_id,
            "source_type": "eFish",
            "filename": uploaded_file.name,
            "row_count": len(df),
            "uploaded_at": datetime.now().isoformat()
        }

        response = supabase.table("file_uploads").insert(record).execute()

        if response.data:
            return True, f"Uploaded {uploaded_file.name} ({len(df)} rows)"
        else:
            return False, "Failed to save upload record"

    except Exception as e:
        return False, f"Error: {e}"
