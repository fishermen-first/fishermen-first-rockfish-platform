"""
File Upload page - Upload data files to Supabase Storage.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from app.config import supabase
from app.auth import require_auth, get_current_user
from app.utils.storage import upload_file
from app.utils.parsers import parse_efish, get_harvest_records, ParseError, ValidationError

# Allowed file types
ALLOWED_EXTENSIONS = ["csv", "xlsx", "xls"]
SOURCE_TYPES = ["eFish", "eLandings", "fish_ticket", "VMS"]


def show():
    """Display the file upload page."""
    if not require_auth():
        st.stop()

    st.title("Upload Data")

    # Initialize session state for preview
    if "upload_preview_data" not in st.session_state:
        st.session_state.upload_preview_data = None
    if "upload_preview_file_upload_id" not in st.session_state:
        st.session_state.upload_preview_file_upload_id = None
    if "upload_preview_error" not in st.session_state:
        st.session_state.upload_preview_error = None

    # Check if we're in preview mode (either with data or with errors)
    if st.session_state.upload_preview_data is not None or st.session_state.upload_preview_error is not None:
        show_preview()
    else:
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
            success, file_upload_id = process_upload(
                file=uploaded_file,
                cooperative_id=selected_coop_id,
                source_type=selected_source_type,
            )

        if success and selected_source_type == "eFish":
            # Parse the file and show preview
            uploaded_file.seek(0)
            try:
                parsed_records = parse_efish(uploaded_file, uploaded_file.name)
                st.session_state.upload_preview_data = parsed_records
                st.session_state.upload_preview_file_upload_id = file_upload_id
                st.session_state.upload_preview_error = None
                st.rerun()
            except ValidationError as e:
                st.session_state.upload_preview_data = None
                st.session_state.upload_preview_error = str(e)
                st.session_state.upload_preview_file_upload_id = file_upload_id
                st.rerun()
            except ParseError as e:
                st.error(f"Parse error: {e}")
        elif success:
            st.success(f"File '{uploaded_file.name}' uploaded successfully!")
            st.rerun()


def show_preview():
    """Display parsed data preview for confirmation."""
    st.subheader("Preview Parsed Data")

    # Check if there's an error
    if st.session_state.upload_preview_error:
        st.error("Validation Errors")
        st.code(st.session_state.upload_preview_error)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cancel", key="upload_preview_cancel_error", use_container_width=True):
                clear_preview_state()
                st.rerun()
        with col2:
            st.info("Fix the errors in your file and try again.")
        return

    # Show parsed data
    parsed_records = st.session_state.upload_preview_data

    if not parsed_records:
        st.warning("No records parsed from the file.")
        if st.button("Back", key="upload_preview_back_empty"):
            clear_preview_state()
            st.rerun()
        return

    st.success(f"Successfully parsed {len(parsed_records)} records")

    # Create preview DataFrame
    preview_data = []
    for rec in parsed_records[:10]:
        preview_data.append({
            "Landed Date": rec.get("landed_date", ""),
            "Vessel": rec.get("_vessel_id_number", ""),
            "Species": rec.get("_species_code", ""),
            "Amount (lbs)": rec.get("amount", 0),
            "Price/lb": rec.get("_price_per_lb", ""),
            "Processor": rec.get("_processor_name", ""),
        })

    preview_df = pd.DataFrame(preview_data)

    st.caption(f"Showing first {min(10, len(parsed_records))} of {len(parsed_records)} records:")
    st.dataframe(
        preview_df,
        use_container_width=True,
        hide_index=True,
        key="upload_preview_table",
    )

    # Confirm/Cancel buttons
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", key="upload_preview_cancel_btn", use_container_width=True):
            clear_preview_state()
            st.rerun()

    with col2:
        if st.button("Confirm & Import", type="primary", key="upload_preview_confirm_btn", use_container_width=True):
            with st.spinner("Importing records..."):
                success = import_harvest_records(
                    parsed_records,
                    st.session_state.upload_preview_file_upload_id
                )

            if success:
                st.success(f"Successfully imported {len(parsed_records)} harvest records!")
                clear_preview_state()
                st.rerun()


def clear_preview_state():
    """Clear preview-related session state."""
    st.session_state.upload_preview_data = None
    st.session_state.upload_preview_file_upload_id = None
    st.session_state.upload_preview_error = None


def import_harvest_records(parsed_records: list[dict], file_upload_id: str) -> bool:
    """
    Insert parsed records into the harvests table.

    Args:
        parsed_records: List of parsed records from parse_efish
        file_upload_id: UUID of the file_uploads record

    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract only harvest table fields (removes underscore-prefixed fields)
        harvest_records = get_harvest_records(parsed_records)

        if not harvest_records:
            st.error("No valid records to import.")
            return False

        # Insert in batches to avoid timeout
        batch_size = 100
        total_inserted = 0

        for i in range(0, len(harvest_records), batch_size):
            batch = harvest_records[i:i + batch_size]
            response = supabase.table("harvests").insert(batch).execute()

            if response.data:
                total_inserted += len(response.data)
            else:
                st.error(f"Failed to insert batch {i // batch_size + 1}")
                return False

        # Update file_uploads with status
        update_response = supabase.table("file_uploads").update({
            "row_count": total_inserted,
            "status": "imported"
        }).eq("id", file_upload_id).execute()

        return True

    except Exception as e:
        st.error(f"Import error: {str(e)}")
        return False


def process_upload(file, cooperative_id: str, source_type: str) -> tuple[bool, str | None]:
    """
    Process and upload the file.

    Args:
        file: Streamlit uploaded file object
        cooperative_id: UUID of the cooperative
        source_type: Type of data source

    Returns:
        Tuple of (success, file_upload_id)
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
            return False, None

        # Log to file_uploads table
        user = get_current_user()
        upload_record = {
            "cooperative_id": cooperative_id,
            "uploaded_by": user.id,
            "source_type": source_type,
            "filename": original_filename,
            "storage_path": storage_path,
            "row_count": row_count,
            "status": "uploaded",  # Will be updated to "imported" after processing
        }

        response = supabase.table("file_uploads").insert(upload_record).execute()

        if not response.data:
            st.error("Failed to log upload to database.")
            return False, None

        file_upload_id = response.data[0]["id"]
        return True, file_upload_id

    except Exception as e:
        st.error(f"Upload error: {str(e)}")
        return False, None


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
    display_cols = ["filename", "source_type", "cooperative_name", "row_count", "status", "uploaded_at", "uploaded_by_email"]
    available_cols = [c for c in display_cols if c in df.columns]
    display_df = df[available_cols].copy()

    if "uploaded_at" in display_df.columns:
        display_df["uploaded_at"] = pd.to_datetime(display_df["uploaded_at"]).dt.strftime("%Y-%m-%d %H:%M")

    # Add status column if not present
    if "status" not in display_df.columns:
        display_df["status"] = "uploaded"

    column_config = {
        "filename": st.column_config.TextColumn("Filename"),
        "source_type": st.column_config.TextColumn("Source"),
        "cooperative_name": st.column_config.TextColumn("Cooperative"),
        "row_count": st.column_config.NumberColumn("Rows", format="%d"),
        "status": st.column_config.TextColumn("Status"),
        "uploaded_at": st.column_config.TextColumn("Uploaded"),
        "uploaded_by_email": st.column_config.TextColumn("By"),
    }

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
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
