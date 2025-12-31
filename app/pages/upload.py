"""
File Upload page - Upload data files to Supabase Storage.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from app.config import supabase
from app.auth import require_auth, get_current_user
from app.utils.storage import upload_file

# Allowed file types
ALLOWED_EXTENSIONS = ["csv", "xlsx", "xls"]
SOURCE_TYPES = ["eFish", "eLandings", "fish_ticket", "VMS"]


def show():
    """Display the file upload page."""
    if not require_auth():
        st.stop()

    st.title("Upload Data")

    # Upload form
    show_upload_form()

    st.divider()

    # Recent uploads
    show_recent_uploads()


def show_upload_form():
    """Display the upload form."""
    st.subheader("Upload New File")

    # Fetch cooperatives for dropdown
    cooperatives = fetch_cooperatives()
    if not cooperatives:
        st.warning("No cooperatives found. Please add cooperatives in Admin Settings first.")
        return

    coop_options = {c["id"]: c["cooperative_name"] for c in cooperatives}
    coop_ids = list(coop_options.keys())

    # Form layout
    col1, col2 = st.columns(2)

    with col1:
        selected_coop_id = st.selectbox(
            "Cooperative *",
            options=coop_ids,
            format_func=lambda x: coop_options.get(x, "Unknown"),
            key="upload_coop_select",
        )

    with col2:
        selected_source_type = st.selectbox(
            "Source Type *",
            options=SOURCE_TYPES,
            key="upload_source_select",
        )

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file (CSV or Excel)",
        type=ALLOWED_EXTENSIONS,
        key="upload_file_input",
    )

    # Upload button
    if st.button("Upload File", type="primary", key="upload_submit_btn", disabled=uploaded_file is None):
        if uploaded_file is None:
            st.error("Please select a file to upload.")
            return

        with st.spinner("Uploading..."):
            success = process_upload(
                file=uploaded_file,
                cooperative_id=selected_coop_id,
                source_type=selected_source_type,
            )

        if success:
            st.success(f"File '{uploaded_file.name}' uploaded successfully!")
            st.rerun()


def process_upload(file, cooperative_id: str, source_type: str) -> bool:
    """
    Process and upload the file.

    Args:
        file: Streamlit uploaded file object
        cooperative_id: UUID of the cooperative
        source_type: Type of data source

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read file content
        file_data = file.getvalue()
        original_filename = file.name

        # Count rows (for metadata)
        row_count = count_rows(file)

        # Upload to Supabase Storage
        folder = source_type.lower()
        success, storage_path, error = upload_file(
            file_data=file_data,
            original_filename=original_filename,
            folder=folder,
        )

        if not success:
            st.error(f"Storage upload failed: {error}")
            return False

        # Log to file_uploads table
        user = get_current_user()
        upload_record = {
            "cooperative_id": cooperative_id,
            "uploaded_by": user.id,
            "source_type": source_type,
            "filename": original_filename,
            "storage_path": storage_path,
            "row_count": row_count,
        }

        response = supabase.table("file_uploads").insert(upload_record).execute()

        if not response.data:
            st.error("Failed to log upload to database.")
            return False

        return True

    except Exception as e:
        st.error(f"Upload error: {str(e)}")
        return False


def count_rows(file) -> int:
    """
    Count rows in the uploaded file.

    Args:
        file: Streamlit uploaded file object

    Returns:
        Number of data rows (excluding header)
    """
    try:
        # Reset file position
        file.seek(0)

        filename = file.name.lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        else:
            return 0

        # Reset file position for actual upload
        file.seek(0)
        return len(df)

    except Exception:
        file.seek(0)
        return 0


def show_recent_uploads():
    """Display recent uploads table."""
    st.subheader("Recent Uploads")

    uploads = fetch_recent_uploads()

    if not uploads:
        st.info("No uploads yet.")
        return

    # Convert to DataFrame for display
    df = pd.DataFrame(uploads)

    # Format for display
    display_df = df[["filename", "source_type", "cooperative_name", "row_count", "uploaded_at", "uploaded_by_email"]].copy()
    display_df["uploaded_at"] = pd.to_datetime(display_df["uploaded_at"]).dt.strftime("%Y-%m-%d %H:%M")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "filename": st.column_config.TextColumn("Filename"),
            "source_type": st.column_config.TextColumn("Source"),
            "cooperative_name": st.column_config.TextColumn("Cooperative"),
            "row_count": st.column_config.NumberColumn("Rows", format="%d"),
            "uploaded_at": st.column_config.TextColumn("Uploaded"),
            "uploaded_by_email": st.column_config.TextColumn("By"),
        },
        key="upload_recent_table",
    )


# =============================================================================
# Data Fetching
# =============================================================================

def fetch_cooperatives() -> list[dict]:
    """Fetch cooperatives for dropdown."""
    try:
        response = supabase.table("cooperatives").select("id, cooperative_name").order("cooperative_name").execute()
        return response.data or []
    except Exception:
        return []


def fetch_recent_uploads(limit: int = 20) -> list[dict]:
    """Fetch recent uploads with cooperative and user info."""
    try:
        response = supabase.table("file_uploads").select("*").order("uploaded_at", desc=True).limit(limit).execute()

        if not response.data:
            return []

        uploads = response.data

        # Get cooperative names
        coop_response = supabase.table("cooperatives").select("id, cooperative_name").execute()
        coop_names = {}
        if coop_response.data:
            coop_names = {c["id"]: c["cooperative_name"] for c in coop_response.data}

        # Get user emails
        user_response = supabase.table("users").select("id, email").execute()
        user_emails = {}
        if user_response.data:
            user_emails = {u["id"]: u["email"] for u in user_response.data}

        # Add display names
        for upload in uploads:
            upload["cooperative_name"] = coop_names.get(upload.get("cooperative_id"), "Unknown")
            upload["uploaded_by_email"] = user_emails.get(upload.get("uploaded_by"), "Unknown")

        return uploads

    except Exception as e:
        st.error(f"Error fetching uploads: {e}")
        return []
