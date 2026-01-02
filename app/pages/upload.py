"""
File Upload page - Upload data files to Supabase Storage.
"""

import streamlit as st
import pandas as pd
from app.config import supabase
from app.auth import require_auth, get_current_user, handle_jwt_error
from app.utils.storage import upload_file
from app.utils.parsers import parse_efish, get_harvest_records, ParseError, ValidationError

ALLOWED_EXTENSIONS = ["csv", "xlsx", "xls"]
SOURCE_TYPES = ["eFish", "eLandings", "fish_ticket", "VMS"]


def show():
    """Display the file upload page."""
    if not require_auth():
        st.stop()

    st.title("Upload Data")
    show_upload_form()
    st.divider()
    show_recent_uploads()


def show_upload_form():
    """Display the upload form."""
    st.subheader("Upload New File")

    cooperatives = fetch_cooperatives()
    if not cooperatives:
        st.warning("No cooperatives found. Please add cooperatives in Admin Settings first.")
        return

    coop_options = {c["id"]: c["cooperative_name"] for c in cooperatives}
    coop_ids = list(coop_options.keys())

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

    uploaded_file = st.file_uploader(
        "Choose a file (CSV or Excel)",
        type=ALLOWED_EXTENSIONS,
        key="upload_file_input",
    )

    if st.button("Upload File", type="primary", key="upload_submit_btn", disabled=uploaded_file is None):
        process_and_import(uploaded_file, selected_coop_id, selected_source_type)


def process_and_import(uploaded_file, cooperative_id: str, source_type: str):
    """Upload file to storage and import if eFish."""
    if uploaded_file is None:
        st.error("Please select a file to upload.")
        return

    # Upload to storage
    with st.spinner("Uploading..."):
        file_data = uploaded_file.getvalue()
        row_count = count_rows(uploaded_file)

        success, storage_path, error = upload_file(
            file_data=file_data,
            original_filename=uploaded_file.name,
            folder=source_type.lower(),
        )

    if not success:
        st.error(f"Upload failed: {error}")
        return

    # Log to file_uploads table
    user = get_current_user()
    response = supabase.table("file_uploads").insert({
        "cooperative_id": cooperative_id,
        "uploaded_by": user.id,
        "source_type": source_type,
        "filename": uploaded_file.name,
        "storage_path": storage_path,
        "row_count": row_count,
        "status": "uploaded",
    }).execute()

    if not response.data:
        st.error("Failed to log upload.")
        return

    file_upload_id = response.data[0]["id"]

    # For eFish: parse and import
    if source_type == "eFish":
        uploaded_file.seek(0)
        try:
            parsed_records = parse_efish(uploaded_file, uploaded_file.name)
            harvest_records = get_harvest_records(parsed_records)

            if harvest_records:
                supabase.table("harvests").insert(harvest_records).execute()
                supabase.table("file_uploads").update({
                    "status": "imported",
                    "row_count": len(harvest_records),
                }).eq("id", file_upload_id).execute()
                st.success(f"Successfully imported {len(harvest_records)} records from {uploaded_file.name}")
            else:
                st.warning("No records to import.")

        except ValidationError as e:
            st.error("Validation errors:")
            st.code(str(e))
            supabase.table("file_uploads").update({"status": "error"}).eq("id", file_upload_id).execute()
        except ParseError as e:
            st.error(f"Parse error: {e}")
            supabase.table("file_uploads").update({"status": "error"}).eq("id", file_upload_id).execute()
    else:
        st.success(f"Uploaded {uploaded_file.name}")


def count_rows(file) -> int:
    """Count rows in uploaded file."""
    try:
        file.seek(0)
        if file.name.lower().endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
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

    df = pd.DataFrame(uploads)
    df["uploaded_at"] = pd.to_datetime(df["uploaded_at"]).dt.strftime("%Y-%m-%d %H:%M")

    st.dataframe(
        df[["filename", "source_type", "cooperative_name", "row_count", "status", "uploaded_at"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "filename": "Filename",
            "source_type": "Source",
            "cooperative_name": "Cooperative",
            "row_count": st.column_config.NumberColumn("Rows", format="%d"),
            "status": "Status",
            "uploaded_at": "Uploaded",
        },
        key="upload_recent_table",
    )


def fetch_cooperatives() -> list[dict]:
    """Fetch cooperatives for dropdown."""
    try:
        response = supabase.table("cooperatives").select("id, cooperative_name").order("cooperative_name").execute()
        return response.data or []
    except Exception as e:
        if handle_jwt_error(e):
            st.rerun()
        return []


def fetch_recent_uploads(limit: int = 20) -> list[dict]:
    """Fetch recent uploads with cooperative names."""
    try:
        response = supabase.table("file_uploads").select("*").order("uploaded_at", desc=True).limit(limit).execute()
        if not response.data:
            return []

        uploads = response.data

        # Get cooperative names
        coop_response = supabase.table("cooperatives").select("id, cooperative_name").execute()
        coop_names = {c["id"]: c["cooperative_name"] for c in coop_response.data} if coop_response.data else {}

        for upload in uploads:
            upload["cooperative_name"] = coop_names.get(upload.get("cooperative_id"), "Unknown")
            upload["status"] = upload.get("status") or "uploaded"

        return uploads
    except Exception as e:
        if handle_jwt_error(e):
            st.rerun()
        return []
