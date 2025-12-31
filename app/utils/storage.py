"""
Supabase Storage utilities for file uploads.
"""

import uuid
from datetime import datetime
from pathlib import Path
from app.config import supabase

BUCKET_NAME = "uploads"


def upload_file(
    file_data: bytes,
    original_filename: str,
    folder: str = "",
    content_type: str | None = None,
) -> tuple[bool, str, str]:
    """
    Upload a file to Supabase Storage.

    Args:
        file_data: The file content as bytes
        original_filename: Original name of the file
        folder: Optional subfolder within the bucket (e.g., "eFish", "eLandings")
        content_type: MIME type of the file (auto-detected if not provided)

    Returns:
        tuple: (success: bool, storage_path: str, error_message: str)
            - success: True if upload succeeded
            - storage_path: Path in storage bucket (empty if failed)
            - error_message: Error description (empty if succeeded)
    """
    try:
        # Generate unique filename
        unique_filename = generate_unique_filename(original_filename)

        # Build storage path
        if folder:
            storage_path = f"{folder}/{unique_filename}"
        else:
            storage_path = unique_filename

        # Auto-detect content type if not provided
        if content_type is None:
            content_type = get_content_type(original_filename)

        # Upload to Supabase Storage
        response = supabase.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": content_type}
        )

        # Check for errors
        if hasattr(response, 'error') and response.error:
            return False, "", f"Upload failed: {response.error}"

        return True, storage_path, ""

    except Exception as e:
        return False, "", f"Upload error: {str(e)}"


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename with timestamp and UUID.

    Args:
        original_filename: Original name of the file

    Returns:
        Unique filename in format: YYYYMMDD_HHMMSS_uuid_original.ext
    """
    # Get file extension
    ext = Path(original_filename).suffix.lower()
    name = Path(original_filename).stem

    # Clean the name (remove special characters, limit length)
    clean_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    clean_name = clean_name[:50]  # Limit length

    # Generate timestamp and short UUID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]

    return f"{timestamp}_{short_uuid}_{clean_name}{ext}"


def get_content_type(filename: str) -> str:
    """
    Get MIME type based on file extension.

    Args:
        filename: Name of the file

    Returns:
        MIME type string
    """
    ext = Path(filename).suffix.lower()

    content_types = {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".json": "application/json",
    }

    return content_types.get(ext, "application/octet-stream")


def get_file_url(storage_path: str) -> str | None:
    """
    Get a public URL for a file in storage.

    Args:
        storage_path: Path to file in the bucket

    Returns:
        Public URL or None if error
    """
    try:
        response = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
        return response
    except Exception:
        return None


def delete_file(storage_path: str) -> tuple[bool, str]:
    """
    Delete a file from storage.

    Args:
        storage_path: Path to file in the bucket

    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        supabase.storage.from_(BUCKET_NAME).remove([storage_path])
        return True, ""
    except Exception as e:
        return False, f"Delete error: {str(e)}"


def list_files(folder: str = "") -> list[dict]:
    """
    List files in a folder.

    Args:
        folder: Folder path within the bucket

    Returns:
        List of file metadata dicts
    """
    try:
        response = supabase.storage.from_(BUCKET_NAME).list(folder)
        return response or []
    except Exception:
        return []
