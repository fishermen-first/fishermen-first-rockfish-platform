"""Unit tests for upload functionality."""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd


class TestBalanceColumnMap:
    """Tests for column mapping constants."""

    def test_balance_column_map_has_required_keys(self):
        """All expected columns are in the mapping."""
        from app.views.upload import BALANCE_COLUMN_MAP

        expected_keys = [
            'Balance Date', 'Account Id', 'Account Name', 'Species Group',
            'Species Group Id', 'Initial Quota', 'Transfers In', 'Transfers Out',
            'Total Quota', 'Total Catch', 'Remaining Quota', 'Percent Taken',
            'Quota Pool Type Code'
        ]

        for key in expected_keys:
            assert key in BALANCE_COLUMN_MAP

    def test_detail_column_map_has_required_keys(self):
        """All expected detail columns are in the mapping."""
        from app.views.upload import DETAIL_COLUMN_MAP

        expected_keys = [
            'Catch Activity Date', 'Processor Permit', 'Vessel Name', 'ADFG',
            'Catch Report Type', 'Haul Number', 'Report Number', 'Landing Date',
            'Gear Code', 'Reporting Area', 'Special Area', 'Species Name',
            'Weight Posted', 'Count Posted', 'Precedence'
        ]

        for key in expected_keys:
            assert key in DETAIL_COLUMN_MAP


class TestImportAccountBalance:
    """Tests for import_account_balance function."""

    @patch('app.config.supabase')
    def test_successful_import(self, mock_supabase):
        """Should return (True, count, None) on successful import."""
        # Mock no duplicates found
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        # Mock successful insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_balance, BALANCE_COLUMN_MAP

        # Create test DataFrame with required columns
        df = pd.DataFrame({
            'Balance Date': ['2026-01-01'],
            'Account Id': ['123'],
            'Account Name': ['CGOA POP CV Coop Silver Bay'],
            'Species Group': ['POP'],
            'Species Group Id': [141],
            'Initial Quota': [10000],
            'Transfers In': [0],
            'Transfers Out': [0],
            'Total Quota': [10000],
            'Total Catch': [5000],
            'Remaining Quota': [5000],
            'Percent Taken': [50.0],
            'Quota Pool Type Code': ['CV']
        })

        success, count, error = import_account_balance(df, 'test.csv')

        assert success is True
        assert count == 1
        assert error is None

    @patch('app.config.supabase')
    def test_duplicate_detection_silver_bay(self, mock_supabase):
        """Should detect and report duplicates for Silver Bay."""
        # Mock duplicate found
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{'id': 'existing'}])

        from app.views.upload import import_account_balance

        df = pd.DataFrame({
            'Balance Date': ['2026-01-01'],
            'Account Name': ['CGOA POP CV Coop Silver Bay'],
        })

        success, count, error = import_account_balance(df, 'test.csv')

        assert success is False
        assert count == 0
        assert 'Silver Bay' in error
        assert '2026-01-01' in error

    @patch('app.config.supabase')
    def test_duplicate_detection_north_pacific(self, mock_supabase):
        """Should detect and report duplicates for North Pacific."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{'id': 'existing'}])

        from app.views.upload import import_account_balance

        df = pd.DataFrame({
            'Balance Date': ['2026-01-05'],
            'Account Name': ['CGOA NR CV Coop North Pacific'],
        })

        success, count, error = import_account_balance(df, 'test.csv')

        assert success is False
        assert 'North Pacific' in error

    @patch('app.config.supabase')
    def test_duplicate_detection_obsi(self, mock_supabase):
        """Should detect and report duplicates for OBSI."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{'id': 'existing'}])

        from app.views.upload import import_account_balance

        df = pd.DataFrame({
            'Balance Date': ['2026-01-05'],
            'Account Name': ['CGOA Dusky CV Coop OBSI'],
        })

        success, count, error = import_account_balance(df, 'test.csv')

        assert success is False
        assert 'OBSI' in error

    @patch('app.config.supabase')
    def test_duplicate_detection_star_of_kodiak(self, mock_supabase):
        """Should detect and report duplicates for Star of Kodiak."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{'id': 'existing'}])

        from app.views.upload import import_account_balance

        df = pd.DataFrame({
            'Balance Date': ['2026-01-05'],
            'Account Name': ['CGOA POP CV Coop Star of Kodiak'],
        })

        success, count, error = import_account_balance(df, 'test.csv')

        assert success is False
        assert 'Star of Kodiak' in error

    @patch('app.config.supabase')
    def test_database_error_handling(self, mock_supabase):
        """Should return error message on database failure."""
        # Mock no duplicates
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        # Mock insert failure
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Connection failed")

        from app.views.upload import import_account_balance, BALANCE_COLUMN_MAP

        df = pd.DataFrame({col: ['test'] for col in BALANCE_COLUMN_MAP.keys()})

        success, count, error = import_account_balance(df, 'test.csv')

        assert success is False
        assert count == 0
        assert "Connection failed" in error

    @patch('app.config.supabase')
    def test_adds_source_file_metadata(self, mock_supabase):
        """Should add source_file to imported records."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_balance, BALANCE_COLUMN_MAP

        df = pd.DataFrame({col: ['test'] for col in BALANCE_COLUMN_MAP.keys()})

        import_account_balance(df, 'my_upload.csv')

        # Check that insert was called with source_file
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args[0]['source_file'] == 'my_upload.csv'


class TestImportAccountDetail:
    """Tests for import_account_detail function."""

    @patch('app.config.supabase')
    def test_successful_import(self, mock_supabase):
        """Should return (True, count, None) on successful import."""
        # Mock no duplicates
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
        # Mock successful insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_detail, DETAIL_COLUMN_MAP

        df = pd.DataFrame({
            'Catch Activity Date': [pd.Timestamp('2026-01-01')],
            'Processor Permit': ['PP123'],
            'Vessel Name': ['Test Vessel'],
            'ADFG': ['12345'],
            'Catch Report Type': ['Landing'],
            'Haul Number': [1],
            'Report Number': ['RPT001'],
            'Landing Date': [pd.Timestamp('2026-01-01')],
            'Gear Code': ['TRW'],
            'Reporting Area': ['630'],
            'Special Area': [''],
            'Species Name': ['Pacific Ocean Perch'],
            'Weight Posted': [1000],
            'Count Posted': [100],
            'Precedence': [1]
        })

        success, count, error = import_account_detail(df, 'test.xlsx')

        assert success is True
        assert count == 1
        assert error is None

    @patch('app.config.supabase')
    def test_duplicate_report_number_detection(self, mock_supabase):
        """Should detect duplicate report numbers."""
        # Mock duplicates found
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = MagicMock(
            data=[{'report_number': 'RPT001'}, {'report_number': 'RPT002'}]
        )

        from app.views.upload import import_account_detail

        df = pd.DataFrame({
            'Report Number': ['RPT001', 'RPT002', 'RPT003'],
            'Catch Activity Date': [None, None, None],
            'Landing Date': [None, None, None],
        })

        success, count, error = import_account_detail(df, 'test.xlsx')

        assert success is False
        assert count == 0
        assert '2 report number' in error

    @patch('app.config.supabase')
    def test_date_conversion(self, mock_supabase):
        """Should convert date columns to ISO format strings."""
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_detail

        df = pd.DataFrame({
            'Catch Activity Date': [pd.Timestamp('2026-03-15')],
            'Processor Permit': ['PP123'],
            'Vessel Name': ['Test'],
            'ADFG': ['12345'],
            'Catch Report Type': ['Landing'],
            'Haul Number': [1],
            'Report Number': ['RPT001'],
            'Landing Date': [pd.Timestamp('2026-03-16')],
            'Gear Code': ['TRW'],
            'Reporting Area': ['630'],
            'Special Area': [''],
            'Species Name': ['POP'],
            'Weight Posted': [1000],
            'Count Posted': [100],
            'Precedence': [1]
        })

        import_account_detail(df, 'test.xlsx')

        # Check dates were converted
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args[0]['catch_activity_date'] == '2026-03-15'
        assert call_args[0]['landing_date'] == '2026-03-16'

    @patch('app.config.supabase')
    def test_handles_null_dates(self, mock_supabase):
        """Should handle NULL/NaT dates gracefully."""
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_detail

        df = pd.DataFrame({
            'Catch Activity Date': [pd.NaT],
            'Processor Permit': ['PP123'],
            'Vessel Name': ['Test'],
            'ADFG': ['12345'],
            'Catch Report Type': ['Landing'],
            'Haul Number': [1],
            'Report Number': ['RPT001'],
            'Landing Date': [pd.NaT],
            'Gear Code': ['TRW'],
            'Reporting Area': ['630'],
            'Special Area': [''],
            'Species Name': ['POP'],
            'Weight Posted': [1000],
            'Count Posted': [100],
            'Precedence': [1]
        })

        success, count, error = import_account_detail(df, 'test.xlsx')

        assert success is True
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args[0]['catch_activity_date'] is None
        assert call_args[0]['landing_date'] is None

    @patch('app.config.supabase')
    def test_handles_nan_values(self, mock_supabase):
        """Should convert NaN values to None for JSON serialization."""
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_detail
        import numpy as np

        df = pd.DataFrame({
            'Catch Activity Date': [None],
            'Processor Permit': [np.nan],
            'Vessel Name': ['Test'],
            'ADFG': ['12345'],
            'Catch Report Type': ['Landing'],
            'Haul Number': [np.nan],
            'Report Number': ['RPT001'],
            'Landing Date': [None],
            'Gear Code': ['TRW'],
            'Reporting Area': ['630'],
            'Special Area': [np.nan],
            'Species Name': ['POP'],
            'Weight Posted': [1000],
            'Count Posted': [np.nan],
            'Precedence': [1]
        })

        success, count, error = import_account_detail(df, 'test.xlsx')

        # Should succeed without JSON serialization errors
        assert success is True

    @patch('app.config.supabase')
    def test_database_error_handling(self, mock_supabase):
        """Should return error on database failure."""
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB Error")

        from app.views.upload import import_account_detail, DETAIL_COLUMN_MAP

        df = pd.DataFrame({col: ['test'] for col in DETAIL_COLUMN_MAP.keys()})
        df['Report Number'] = ['RPT001']
        df['Catch Activity Date'] = [None]
        df['Landing Date'] = [None]

        success, count, error = import_account_detail(df, 'test.xlsx')

        assert success is False
        assert "DB Error" in error

    @patch('app.config.supabase')
    def test_empty_report_numbers_handled(self, mock_supabase):
        """Should handle empty/null report numbers."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_detail, DETAIL_COLUMN_MAP

        df = pd.DataFrame({col: ['test'] for col in DETAIL_COLUMN_MAP.keys()})
        df['Report Number'] = [None]  # No report numbers
        df['Catch Activity Date'] = [None]
        df['Landing Date'] = [None]

        success, count, error = import_account_detail(df, 'test.xlsx')

        # Should still work - just won't check for duplicates
        assert success is True


class TestColumnValidation:
    """Tests for column validation logic."""

    def test_missing_balance_columns_detected(self):
        """Should identify missing columns in balance CSV."""
        from app.views.upload import BALANCE_COLUMN_MAP

        df = pd.DataFrame({
            'Balance Date': ['2026-01-01'],
            'Account Name': ['Test']
            # Missing many columns
        })

        required_cols = list(BALANCE_COLUMN_MAP.keys())
        missing_cols = [c for c in required_cols if c not in df.columns]

        assert len(missing_cols) > 0
        assert 'Initial Quota' in missing_cols
        assert 'Total Catch' in missing_cols

    def test_all_balance_columns_present(self):
        """Should pass when all columns present."""
        from app.views.upload import BALANCE_COLUMN_MAP

        df = pd.DataFrame({col: ['test'] for col in BALANCE_COLUMN_MAP.keys()})

        required_cols = list(BALANCE_COLUMN_MAP.keys())
        missing_cols = [c for c in required_cols if c not in df.columns]

        assert len(missing_cols) == 0

    def test_missing_detail_columns_detected(self):
        """Should identify missing columns in detail Excel."""
        from app.views.upload import DETAIL_COLUMN_MAP

        df = pd.DataFrame({
            'Vessel Name': ['Test'],
            'Report Number': ['RPT001']
            # Missing many columns
        })

        required_cols = list(DETAIL_COLUMN_MAP.keys())
        missing_cols = [c for c in required_cols if c not in df.columns]

        assert len(missing_cols) > 0
        assert 'Catch Activity Date' in missing_cols
        assert 'Weight Posted' in missing_cols


class TestUploadEdgeCases:
    """Edge case tests for upload functionality."""

    def test_csv_with_extra_columns(self):
        """Should handle CSV with extra columns not in mapping."""
        from app.views.upload import BALANCE_COLUMN_MAP

        df = pd.DataFrame({col: ['test'] for col in BALANCE_COLUMN_MAP.keys()})
        df['Extra Column 1'] = ['extra1']
        df['Extra Column 2'] = ['extra2']

        required_cols = list(BALANCE_COLUMN_MAP.keys())
        missing_cols = [c for c in required_cols if c not in df.columns]

        # Extra columns should not cause missing columns
        assert len(missing_cols) == 0

    def test_csv_with_reordered_columns(self):
        """Should handle CSV with columns in different order."""
        from app.views.upload import BALANCE_COLUMN_MAP

        # Create with reversed column order
        cols = list(BALANCE_COLUMN_MAP.keys())
        reversed_cols = cols[::-1]
        df = pd.DataFrame({col: ['test'] for col in reversed_cols})

        required_cols = list(BALANCE_COLUMN_MAP.keys())
        missing_cols = [c for c in required_cols if c not in df.columns]

        assert len(missing_cols) == 0

    @patch('app.config.supabase')
    def test_negative_quota_values(self, mock_supabase):
        """Should handle negative quota values in import."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_balance

        df = pd.DataFrame({
            'Balance Date': ['2026-01-01'],
            'Account Id': ['123'],
            'Account Name': ['CGOA POP CV Coop Silver Bay'],
            'Species Group': ['POP'],
            'Species Group Id': [141],
            'Initial Quota': [10000],
            'Transfers In': [0],
            'Transfers Out': [0],
            'Total Quota': [10000],
            'Total Catch': [15000],  # Overfished
            'Remaining Quota': [-5000],  # Negative remaining
            'Percent Taken': [150.0],
            'Quota Pool Type Code': ['CV']
        })

        success, count, error = import_account_balance(df, 'test.csv')

        # Should still import - negative values are valid data
        assert success is True

    @patch('app.config.supabase')
    def test_duplicate_rows_within_file(self, mock_supabase):
        """Should handle duplicate rows within the same file."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}, {'id': '2'}])

        from app.views.upload import import_account_balance

        df = pd.DataFrame({
            'Balance Date': ['2026-01-01', '2026-01-01'],  # Same date
            'Account Id': ['123', '123'],  # Same account
            'Account Name': ['CGOA POP CV Coop Silver Bay', 'CGOA POP CV Coop Silver Bay'],
            'Species Group': ['POP', 'POP'],  # Same species
            'Species Group Id': [141, 141],
            'Initial Quota': [10000, 10000],
            'Transfers In': [0, 0],
            'Transfers Out': [0, 0],
            'Total Quota': [10000, 10000],
            'Total Catch': [5000, 5000],
            'Remaining Quota': [5000, 5000],
            'Percent Taken': [50.0, 50.0],
            'Quota Pool Type Code': ['CV', 'CV']
        })

        success, count, error = import_account_balance(df, 'test.csv')

        # Documents current behavior - both rows inserted
        # May want to add deduplication in future
        assert success is True
        assert count == 2

    def test_file_with_only_headers(self):
        """Should handle file with headers but no data rows."""
        from app.views.upload import BALANCE_COLUMN_MAP

        df = pd.DataFrame(columns=list(BALANCE_COLUMN_MAP.keys()))

        assert len(df) == 0
        assert list(df.columns) == list(BALANCE_COLUMN_MAP.keys())

    @patch('app.config.supabase')
    def test_empty_dataframe_import(self, mock_supabase):
        """Should handle empty dataframe gracefully."""
        from app.views.upload import import_account_balance, BALANCE_COLUMN_MAP

        df = pd.DataFrame(columns=list(BALANCE_COLUMN_MAP.keys()))

        success, count, error = import_account_balance(df, 'empty.csv')

        # Should succeed with 0 records
        assert success is True
        assert count == 0

    @patch('app.config.supabase')
    def test_whitespace_in_column_names(self, mock_supabase):
        """Should handle columns with leading/trailing whitespace."""
        from app.views.upload import BALANCE_COLUMN_MAP

        # Simulate columns with whitespace (common Excel export issue)
        cols_with_spaces = {f' {col} ': ['test'] for col in BALANCE_COLUMN_MAP.keys()}
        df = pd.DataFrame(cols_with_spaces)

        # Strip column names
        df.columns = df.columns.str.strip()

        required_cols = list(BALANCE_COLUMN_MAP.keys())
        missing_cols = [c for c in required_cols if c not in df.columns]

        assert len(missing_cols) == 0

    @patch('app.config.supabase')
    def test_unicode_in_vessel_names(self, mock_supabase):
        """Should handle unicode characters in vessel/account names."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_balance

        df = pd.DataFrame({
            'Balance Date': ['2026-01-01'],
            'Account Id': ['123'],
            'Account Name': ['CGOA POP CV Coop Señor Pescador'],  # Unicode
            'Species Group': ['POP'],
            'Species Group Id': [141],
            'Initial Quota': [10000],
            'Transfers In': [0],
            'Transfers Out': [0],
            'Total Quota': [10000],
            'Total Catch': [5000],
            'Remaining Quota': [5000],
            'Percent Taken': [50.0],
            'Quota Pool Type Code': ['CV']
        })

        success, count, error = import_account_balance(df, 'test.csv')

        assert success is True

    @patch('app.config.supabase')
    def test_very_large_quota_values(self, mock_supabase):
        """Should handle very large quota values."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_balance

        df = pd.DataFrame({
            'Balance Date': ['2026-01-01'],
            'Account Id': ['123'],
            'Account Name': ['CGOA POP CV Coop Silver Bay'],
            'Species Group': ['POP'],
            'Species Group Id': [141],
            'Initial Quota': [999999999],  # Very large
            'Transfers In': [0],
            'Transfers Out': [0],
            'Total Quota': [999999999],
            'Total Catch': [0],
            'Remaining Quota': [999999999],
            'Percent Taken': [0.0],
            'Quota Pool Type Code': ['CV']
        })

        success, count, error = import_account_balance(df, 'test.csv')

        assert success is True

    @patch('app.config.supabase')
    def test_detail_with_special_characters_in_report_number(self, mock_supabase):
        """Should handle special characters in report numbers."""
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_detail

        df = pd.DataFrame({
            'Catch Activity Date': [pd.Timestamp('2026-01-01')],
            'Processor Permit': ['PP123'],
            'Vessel Name': ['Test Vessel'],
            'ADFG': ['12345'],
            'Catch Report Type': ['Landing'],
            'Haul Number': [1],
            'Report Number': ['RPT-001/A'],  # Special chars
            'Landing Date': [pd.Timestamp('2026-01-01')],
            'Gear Code': ['TRW'],
            'Reporting Area': ['630'],
            'Special Area': [''],
            'Species Name': ['Pacific Ocean Perch'],
            'Weight Posted': [1000],
            'Count Posted': [100],
            'Precedence': [1]
        })

        success, count, error = import_account_detail(df, 'test.xlsx')

        assert success is True

    @patch('app.config.supabase')
    def test_zero_weight_posted(self, mock_supabase):
        """Should handle zero weight posted records."""
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{'id': '1'}])

        from app.views.upload import import_account_detail

        df = pd.DataFrame({
            'Catch Activity Date': [pd.Timestamp('2026-01-01')],
            'Processor Permit': ['PP123'],
            'Vessel Name': ['Test Vessel'],
            'ADFG': ['12345'],
            'Catch Report Type': ['Landing'],
            'Haul Number': [1],
            'Report Number': ['RPT001'],
            'Landing Date': [pd.Timestamp('2026-01-01')],
            'Gear Code': ['TRW'],
            'Reporting Area': ['630'],
            'Special Area': [''],
            'Species Name': ['Pacific Ocean Perch'],
            'Weight Posted': [0],  # Zero weight
            'Count Posted': [0],
            'Precedence': [1]
        })

        success, count, error = import_account_detail(df, 'test.xlsx')

        assert success is True
