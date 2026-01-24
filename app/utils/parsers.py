"""
File parsers for various data sources.
"""

import pandas as pd
from datetime import date
from typing import BinaryIO
from app.config import supabase


class ParseError(Exception):
    """Custom exception for parsing errors."""
    pass


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


# Required columns for eFish files
EFISH_REQUIRED_COLUMNS = [
    "landing_date",
    "vessel_name",
    "vessel_id",
    "species_code",
    "species_name",
    "pounds",
    "price_per_lb",
    "processor_name",
]


def parse_efish(file: BinaryIO, filename: str) -> list[dict]:
    """
    Parse an eFish data file and return validated records.

    Args:
        file: File-like object (from Streamlit uploader or open file)
        filename: Original filename (to determine file type)

    Returns:
        List of validated records ready for insert into harvests table

    Raises:
        ParseError: If file cannot be read or parsed
        ValidationError: If required columns are missing or data is invalid
    """
    # Read file into DataFrame
    df = read_file(file, filename)

    # Validate required columns
    validate_columns(df, EFISH_REQUIRED_COLUMNS)

    # Clean column names (lowercase, strip whitespace)
    df.columns = df.columns.str.lower().str.strip()

    # Fetch lookup tables
    vessels = fetch_vessels_lookup()
    species = fetch_species_lookup()
    processors = fetch_processors_lookup()
    seasons = fetch_seasons_lookup()

    # Parse and validate each row
    records = []
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # Account for header row and 0-indexing

        try:
            record = parse_efish_row(row, row_num, vessels, species, processors, seasons)
            records.append(record)
        except ValidationError as e:
            errors.append(str(e))

    # If there were errors, raise them all
    if errors:
        error_summary = f"Found {len(errors)} validation error(s):\n" + "\n".join(errors[:10])
        if len(errors) > 10:
            error_summary += f"\n... and {len(errors) - 10} more errors"
        raise ValidationError(error_summary)

    return records


def read_file(file: BinaryIO, filename: str) -> pd.DataFrame:
    """
    Read a CSV or Excel file into a DataFrame.

    Args:
        file: File-like object
        filename: Original filename

    Returns:
        pandas DataFrame

    Raises:
        ParseError: If file cannot be read
    """
    try:
        filename_lower = filename.lower()

        if filename_lower.endswith(".csv"):
            df = pd.read_csv(file)
        elif filename_lower.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        else:
            raise ParseError(f"Unsupported file type: {filename}")

        if df.empty:
            raise ParseError("File is empty or contains no data rows")

        return df

    except pd.errors.EmptyDataError:
        raise ParseError("File is empty")
    except pd.errors.ParserError as e:
        raise ParseError(f"Could not parse file: {str(e)}")
    except Exception as e:
        raise ParseError(f"Error reading file: {str(e)}")


def validate_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    """
    Validate that all required columns exist in the DataFrame.

    Args:
        df: pandas DataFrame
        required_columns: List of required column names

    Raises:
        ValidationError: If any required columns are missing
    """
    # Normalize column names for comparison
    df_columns = [c.lower().strip() for c in df.columns]

    missing = []
    for col in required_columns:
        if col.lower() not in df_columns:
            missing.append(col)

    if missing:
        raise ValidationError(
            f"Missing required columns: {', '.join(missing)}. "
            f"Found columns: {', '.join(df.columns.tolist())}"
        )


def parse_efish_row(
    row: pd.Series,
    row_num: int,
    vessels: dict,
    species: dict,
    processors: dict,
    seasons: dict,
) -> dict:
    """
    Parse and validate a single eFish row.

    Args:
        row: pandas Series representing one row
        row_num: Row number for error messages
        vessels: Dict mapping vessel_id_number to UUID
        species: Dict mapping species_code to UUID
        processors: Dict mapping processor_name to UUID
        seasons: Dict mapping year to season UUID

    Returns:
        Validated record dict ready for insert

    Raises:
        ValidationError: If row data is invalid
    """
    errors = []

    # Parse landing date
    landing_date = None
    try:
        landing_date_raw = row.get("landing_date")
        if pd.isna(landing_date_raw):
            errors.append("landing_date is required")
        else:
            if isinstance(landing_date_raw, str):
                landing_date = pd.to_datetime(landing_date_raw).date()
            elif isinstance(landing_date_raw, pd.Timestamp):
                landing_date = landing_date_raw.date()
            elif isinstance(landing_date_raw, date):
                landing_date = landing_date_raw
            else:
                landing_date = pd.to_datetime(landing_date_raw).date()
    except Exception:
        errors.append(f"Invalid landing_date format: {row.get('landing_date')}")

    # Look up vessel
    vessel_id = None
    vessel_id_number = str(row.get("vessel_id", "")).strip()
    if not vessel_id_number or pd.isna(row.get("vessel_id")):
        errors.append("vessel_id is required")
    elif vessel_id_number not in vessels:
        errors.append(f"Unknown vessel_id: {vessel_id_number}")
    else:
        vessel_id = vessels[vessel_id_number]

    # Look up species
    species_id = None
    species_code = str(row.get("species_code", "")).strip()
    if not species_code or pd.isna(row.get("species_code")):
        errors.append("species_code is required")
    elif species_code not in species:
        errors.append(f"Unknown species_code: {species_code}")
    else:
        species_id = species[species_code]

    # Look up processor (optional but recommended)
    processor_id = None
    processor_name = str(row.get("processor_name", "")).strip()
    if processor_name and not pd.isna(row.get("processor_name")):
        if processor_name not in processors:
            errors.append(f"Unknown processor_name: {processor_name}")
        else:
            processor_id = processors[processor_name]

    # Look up season based on landing date
    season_id = None
    if landing_date:
        year = landing_date.year
        if year not in seasons:
            errors.append(f"No season found for year: {year}")
        else:
            season_id = seasons[year]

    # Parse pounds (weight)
    weight_lbs = None
    try:
        pounds_raw = row.get("pounds")
        if pd.isna(pounds_raw):
            errors.append("pounds is required")
        else:
            weight_lbs = float(pounds_raw)
            if weight_lbs < 0:
                errors.append("pounds cannot be negative")
    except (ValueError, TypeError):
        errors.append(f"Invalid pounds value: {row.get('pounds')}")

    # Parse price per lb
    price_per_lb = None
    try:
        price_raw = row.get("price_per_lb")
        if not pd.isna(price_raw):
            price_per_lb = float(price_raw)
            if price_per_lb < 0:
                errors.append("price_per_lb cannot be negative")
    except (ValueError, TypeError):
        errors.append(f"Invalid price_per_lb value: {row.get('price_per_lb')}")

    # If there were errors for this row, raise them
    if errors:
        raise ValidationError(f"Row {row_num}: " + "; ".join(errors))

    # Build the record
    record = {
        "season_id": season_id,
        "vessel_id": vessel_id,
        "processor_id": processor_id,
        "species_id": species_id,
        "amount": weight_lbs,
        "landed_date": landing_date.isoformat() if landing_date else None,
        # Additional fields for reference (not in harvests table, but useful)
        "_price_per_lb": price_per_lb,
        "_vessel_id_number": vessel_id_number,
        "_species_code": species_code,
        "_processor_name": processor_name,
    }

    return record


# =============================================================================
# Lookup Table Fetchers
# =============================================================================

def _fetch_lookup(table: str, key_column: str) -> dict:
    """
    Generic helper to fetch a lookup table mapping key_column -> id.

    Args:
        table: Supabase table name
        key_column: Column to use as the key in the returned dict

    Returns:
        Dict mapping key_column values to their UUIDs
    """
    try:
        response = supabase.table(table).select(f"id, {key_column}").execute()
        if response.data:
            return {row[key_column]: row["id"] for row in response.data}
        return {}
    except Exception:
        return {}


def fetch_vessels_lookup() -> dict[str, str]:
    """Fetch vessels: vessel_id_number -> UUID."""
    return _fetch_lookup("vessels", "vessel_id_number")


def fetch_species_lookup() -> dict[str, str]:
    """Fetch species: species_code -> UUID."""
    return _fetch_lookup("species", "species_code")


def fetch_processors_lookup() -> dict[str, str]:
    """Fetch processors: processor_name -> UUID."""
    return _fetch_lookup("processors", "processor_name")


def fetch_seasons_lookup() -> dict[int, str]:
    """Fetch seasons: year -> UUID."""
    return _fetch_lookup("seasons", "year")


def get_harvest_records(parsed_records: list[dict]) -> list[dict]:
    """
    Extract only the harvest table fields from parsed records.
    Removes fields prefixed with underscore.

    Args:
        parsed_records: List of parsed records from parse_efish

    Returns:
        List of records ready for insert into harvests table
    """
    harvest_records = []
    for record in parsed_records:
        harvest_record = {k: v for k, v in record.items() if not k.startswith("_")}
        harvest_records.append(harvest_record)
    return harvest_records
