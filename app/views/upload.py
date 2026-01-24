"""Upload page - file uploads for eFish data."""

import streamlit as st
import pandas as pd

# Column mapping for Account Balance CSV
BALANCE_COLUMN_MAP = {
    'Balance Date': 'balance_date',
    'Account Id': 'account_id',
    'Account Name': 'account_name',
    'Species Group': 'species_group',
    'Species Group Id': 'species_group_id',
    'Initial Quota': 'initial_quota',
    'Transfers In': 'transfers_in',
    'Transfers Out': 'transfers_out',
    'Total Quota': 'total_quota',
    'Total Catch': 'total_catch',
    'Remaining Quota': 'remaining_quota',
    'Percent Taken': 'percent_taken',
    'Quota Pool Type Code': 'quota_pool_type_code'
}

def detect_balance_duplicates(df):
    """
    Detect duplicate rows within an account balance file.

    Duplicates are based on: Balance Date + Account Id + Species Group Id

    Returns:
        Tuple of (has_duplicates: bool, duplicate_count: int, duplicate_info: str)
    """
    key_cols = ['Balance Date', 'Account Id', 'Species Group Id']

    # Check if all key columns exist
    missing = [c for c in key_cols if c not in df.columns]
    if missing:
        return False, 0, ""

    duplicates = df[df.duplicated(subset=key_cols, keep=False)]

    if len(duplicates) > 0:
        dup_count = len(duplicates) - len(df[df.duplicated(subset=key_cols, keep='first')])
        # Get sample of what's duplicated
        dup_sample = duplicates.groupby(key_cols).size().reset_index(name='count')
        dup_sample = dup_sample[dup_sample['count'] > 1].head(3)

        info_parts = []
        for _, row in dup_sample.iterrows():
            info_parts.append(f"{row['Account Id']} / {row['Species Group Id']} on {row['Balance Date']}")

        info = f"Found {dup_count} duplicate row(s). Examples: {'; '.join(info_parts)}"
        return True, dup_count, info

    return False, 0, ""


def detect_detail_duplicates(df):
    """
    Detect duplicate rows within an account detail file.

    Duplicates are based on: Report Number

    Returns:
        Tuple of (has_duplicates: bool, duplicate_count: int, duplicate_info: str)
    """
    if 'Report Number' not in df.columns:
        return False, 0, ""

    # Only check non-null report numbers
    report_nums = df['Report Number'].dropna()
    duplicates = report_nums[report_nums.duplicated(keep=False)]

    if len(duplicates) > 0:
        dup_count = len(duplicates) - len(report_nums[report_nums.duplicated(keep='first')])
        unique_dups = duplicates.unique()[:5]  # Show up to 5 examples

        info = f"Found {dup_count} duplicate report number(s): {', '.join(str(x) for x in unique_dups)}"
        return True, dup_count, info

    return False, 0, ""


# Column mapping for Account Detail Excel
DETAIL_COLUMN_MAP = {
    'Catch Activity Date': 'catch_activity_date',
    'Processor Permit': 'processor_permit',
    'Vessel Name': 'vessel_name',
    'ADFG': 'adfg',
    'Catch Report Type': 'catch_report_type',
    'Haul Number': 'haul_number',
    'Report Number': 'report_number',
    'Landing Date': 'landing_date',
    'Gear Code': 'gear_code',
    'Reporting Area': 'reporting_area',
    'Special Area': 'special_area',
    'Species Name': 'species_name',
    'Weight Posted': 'weight_posted',
    'Count Posted': 'count_posted',
    'Precedence': 'precedence'
}


def import_account_balance(df, filename):
    """Import account balance data into account_balances_raw table."""
    from app.config import supabase

    # Get unique balance_date and account_name combinations from uploaded file
    unique_combos = df[['Balance Date', 'Account Name']].drop_duplicates()

    # Check for existing records
    duplicates = []
    for _, row in unique_combos.iterrows():
        existing = supabase.table("account_balances_raw")\
            .select("id")\
            .eq("balance_date", row['Balance Date'])\
            .eq("account_name", row['Account Name'])\
            .execute()

        if existing.data:
            # Extract co-op name from account name (e.g., "Silver Bay" from "CGOA POP CV Coop Silver Bay")
            account_name = row['Account Name']
            if 'Silver Bay' in account_name:
                coop = 'Silver Bay'
            elif 'North Pacific' in account_name:
                coop = 'North Pacific'
            elif 'OBSI' in account_name:
                coop = 'OBSI'
            elif 'Star of Kodiak' in account_name:
                coop = 'Star of Kodiak'
            else:
                coop = account_name

            date = row['Balance Date']
            coop_date = f"{coop} ({date})"
            if coop_date not in duplicates:
                duplicates.append(coop_date)

    if duplicates:
        return False, 0, f"Data already exists for: {', '.join(duplicates)}"

    # Rename columns to match database
    df_import = df.rename(columns=BALANCE_COLUMN_MAP)

    # Add metadata
    df_import['source_file'] = filename

    # Convert to list of dicts for insert
    records = df_import.to_dict('records')

    # Insert into database
    try:
        response = supabase.table('account_balances_raw').insert(records).execute()
        return True, len(records), None
    except Exception as e:
        return False, 0, str(e)


def import_account_detail(df, filename):
    """Import account detail data into account_detail_raw table."""
    from app.config import supabase

    # Check for duplicates using report_number
    report_numbers = df['Report Number'].dropna().unique().tolist()

    if report_numbers:
        # Check which report numbers already exist
        existing = supabase.table("account_detail_raw")\
            .select("report_number")\
            .in_("report_number", [str(rn) for rn in report_numbers])\
            .execute()

        if existing.data:
            existing_count = len(existing.data)
            return False, 0, f"Data already exists for {existing_count} report number(s). Upload rejected."

    # Rename columns to match database
    df_import = df.rename(columns=DETAIL_COLUMN_MAP)

    # Add metadata
    df_import['source_file'] = filename

    # Convert date columns to strings for JSON serialization
    date_columns = ['catch_activity_date', 'landing_date']
    for col in date_columns:
        if col in df_import.columns:
            df_import[col] = df_import[col].apply(
                lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None
            )

    # Handle NaN values - convert to None for database
    df_import = df_import.where(pd.notnull(df_import), None)

    # Convert to list of dicts for insert
    records = df_import.to_dict('records')

    # Replace nan with None (JSON doesn't support nan)
    import math
    for record in records:
        for key, value in record.items():
            if isinstance(value, float) and math.isnan(value):
                record[key] = None

    # Insert into database
    try:
        if records:
            response = supabase.table('account_detail_raw').insert(records).execute()
        return True, len(records), None
    except Exception as e:
        return False, 0, str(e)


def show():
    """Display the upload page with two upload sections."""
    from app.utils.styles import page_header, section_header
    page_header("Upload", "eFish data imports for reconciliation")

    # Section 1: Account Balance
    section_header("ACCOUNT BALANCE", "📊")
    st.caption("Upload coopaccountbalance.csv - Summary snapshot by species")

    balance_file = st.file_uploader("Choose CSV file", type=['csv'], key="balance_upload")

    if balance_file:
        try:
            df = pd.read_csv(balance_file)
            st.write(f"Preview: {len(df)} rows")
            st.dataframe(df, use_container_width=True)

            # Validate columns
            required_cols = list(BALANCE_COLUMN_MAP.keys())
            missing_cols = [c for c in required_cols if c not in df.columns]

            if missing_cols:
                st.error(f"Missing required columns: {missing_cols}")
            else:
                # Check for duplicates within the file
                has_dups, dup_count, dup_info = detect_balance_duplicates(df)
                if has_dups:
                    st.warning(f"Warning: {dup_info}")

                if st.button("Import Account Balance", key="import_balance"):
                    success, count, error = import_account_balance(df, balance_file.name)

                    if success:
                        st.success(f"Successfully imported {count} records")
                    elif error and error.startswith("Data already"):
                        st.warning(f"{error}")
                    else:
                        st.error(f"Import failed: {error}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.divider()

    # Section 2: Catch Detail
    section_header("CATCH DETAIL", "📋")
    st.caption("Upload coopaccountdetail.xlsx - Individual harvest records")

    detail_file = st.file_uploader("Choose Excel file", type=['xlsx'], key="detail_upload")

    if detail_file:
        try:
            df = pd.read_excel(detail_file)
            st.write(f"Preview: {len(df)} rows")
            st.dataframe(df, use_container_width=True)

            # Validate columns
            required_cols = list(DETAIL_COLUMN_MAP.keys())
            missing_cols = [c for c in required_cols if c not in df.columns]

            if missing_cols:
                st.error(f"Missing required columns: {missing_cols}")
            else:
                # Check for duplicates within the file
                has_dups, dup_count, dup_info = detect_detail_duplicates(df)
                if has_dups:
                    st.warning(f"Warning: {dup_info}")

                if st.button("Import Catch Detail", key="import_detail"):
                    success, count, error = import_account_detail(df, detail_file.name)

                    if success:
                        st.success(f"Successfully imported {count} records")
                    elif error and "already exists" in error:
                        st.warning(f"{error}")
                    else:
                        st.error(f"Import failed: {error}")
        except Exception as e:
            st.error(f"Error reading file: {e}")
