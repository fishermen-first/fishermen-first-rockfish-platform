"""Unit tests for dashboard functionality."""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd


class TestSpeciesMap:
    """Tests for species mapping constant."""

    def test_species_map_contains_target_species(self):
        """Should contain POP, NR, and Dusky mappings."""
        from app.views.dashboard import SPECIES_MAP

        assert SPECIES_MAP[141] == 'POP'
        assert SPECIES_MAP[136] == 'NR'
        assert SPECIES_MAP[172] == 'Dusky'

    def test_species_map_excludes_psc(self):
        """Should not contain PSC species."""
        from app.views.dashboard import SPECIES_MAP

        assert 200 not in SPECIES_MAP  # Halibut
        assert 110 not in SPECIES_MAP  # Pacific Cod


class TestGetRiskLevel:
    """Tests for get_risk_level function (from shared formatting module)."""

    def test_critical_under_10_percent(self):
        """Should return 'critical' for <10%."""
        from app.utils.formatting import get_risk_level

        assert get_risk_level(0) == 'critical'
        assert get_risk_level(5) == 'critical'
        assert get_risk_level(9.9) == 'critical'

    def test_warning_10_to_50_percent(self):
        """Should return 'warning' for 10-50%."""
        from app.utils.formatting import get_risk_level

        assert get_risk_level(10) == 'warning'
        assert get_risk_level(25) == 'warning'
        assert get_risk_level(49.9) == 'warning'

    def test_ok_over_50_percent(self):
        """Should return 'ok' for >50%."""
        from app.utils.formatting import get_risk_level

        assert get_risk_level(50) == 'ok'
        assert get_risk_level(75) == 'ok'
        assert get_risk_level(100) == 'ok'

    def test_na_for_none(self):
        """Should return 'na' for None."""
        from app.utils.formatting import get_risk_level

        assert get_risk_level(None) == 'na'

    def test_na_for_nan_via_wrapper(self):
        """Dashboard's wrapper should return 'na' for NaN values in DataFrames."""
        import numpy as np
        from app.views.dashboard import _get_risk_level_for_df

        # The base get_risk_level doesn't handle np.nan specially,
        # but the dashboard wrapper _get_risk_level_for_df does
        assert _get_risk_level_for_df(np.nan) == 'na'


class TestFormatLbs:
    """Tests for format_lbs function (from shared formatting module)."""

    def test_formats_millions(self):
        """Should format millions with M suffix."""
        from app.utils.formatting import format_lbs

        assert format_lbs(1_000_000) == '1.0M'
        assert format_lbs(2_500_000) == '2.5M'
        assert format_lbs(10_000_000) == '10.0M'

    def test_formats_thousands(self):
        """Should format thousands with K suffix."""
        from app.utils.formatting import format_lbs

        assert format_lbs(1_000) == '1.0K'
        assert format_lbs(5_500) == '5.5K'
        assert format_lbs(999_000) == '999.0K'

    def test_formats_small_numbers(self):
        """Should format small numbers as-is."""
        from app.utils.formatting import format_lbs

        assert format_lbs(0) == '0'
        assert format_lbs(500) == '500'
        assert format_lbs(999) == '999'


class TestGetPctColor:
    """Tests for get_pct_color function (from shared formatting module)."""

    def test_red_for_critical(self):
        """Should return red for <10%."""
        from app.utils.formatting import get_pct_color

        assert get_pct_color(5) == '#dc2626'
        assert get_pct_color(9.9) == '#dc2626'

    def test_amber_for_warning(self):
        """Should return amber for 10-50%."""
        from app.utils.formatting import get_pct_color

        assert get_pct_color(10) == '#d97706'
        assert get_pct_color(49) == '#d97706'

    def test_green_for_ok(self):
        """Should return green for >=50% (standardized across views)."""
        from app.utils.formatting import get_pct_color

        # Standardized to green #059669 (was dark #1e293b in dashboard only)
        assert get_pct_color(50) == '#059669'
        assert get_pct_color(100) == '#059669'

    def test_custom_ok_color(self):
        """Should allow custom color for ok status (e.g., dashboard uses dark)."""
        from app.utils.formatting import get_pct_color

        # Dashboard passes ok_color="#1e293b" to preserve original appearance
        assert get_pct_color(50, ok_color="#1e293b") == '#1e293b'
        assert get_pct_color(100, ok_color="#1e293b") == '#1e293b'


class TestPivotQuotaData:
    """Tests for pivot_quota_data function."""

    def test_empty_dataframe_returns_empty(self):
        """Should return empty DataFrame for empty input."""
        from app.views.dashboard import pivot_quota_data

        result = pivot_quota_data(pd.DataFrame())

        assert result.empty

    def test_pivots_species_to_columns(self):
        """Should create columns for each species."""
        from app.views.dashboard import pivot_quota_data

        df = pd.DataFrame({
            'llp': ['LLP1', 'LLP1', 'LLP1'],
            'vessel_name': ['Vessel 1', 'Vessel 1', 'Vessel 1'],
            'coop_code': ['SB', 'SB', 'SB'],
            'species': ['POP', 'NR', 'Dusky'],
            'remaining_lbs': [5000, 3000, 2000],
            'allocation_lbs': [10000, 6000, 4000],
            'pct_remaining': [50.0, 50.0, 50.0]
        })

        result = pivot_quota_data(df)

        assert len(result) == 1
        assert 'POP_remaining_lbs' in result.columns
        assert 'NR_remaining_lbs' in result.columns
        assert 'Dusky_remaining_lbs' in result.columns

    def test_preserves_vessel_info(self):
        """Should keep llp, vessel_name, coop_code."""
        from app.views.dashboard import pivot_quota_data

        df = pd.DataFrame({
            'llp': ['LLP123'],
            'vessel_name': ['Test Vessel'],
            'coop_code': ['NP'],
            'species': ['POP'],
            'remaining_lbs': [5000],
            'allocation_lbs': [10000],
            'pct_remaining': [50.0]
        })

        result = pivot_quota_data(df)

        assert result.iloc[0]['llp'] == 'LLP123'
        assert result.iloc[0]['vessel_name'] == 'Test Vessel'
        assert result.iloc[0]['coop_code'] == 'NP'


class TestAddRiskFlags:
    """Tests for add_risk_flags function."""

    def test_adds_species_risk_columns(self):
        """Should add risk column for each species."""
        from app.views.dashboard import add_risk_flags

        df = pd.DataFrame({
            'llp': ['LLP1'],
            'POP_pct_remaining': [5.0],
            'NR_pct_remaining': [25.0],
            'Dusky_pct_remaining': [75.0]
        })

        result = add_risk_flags(df)

        assert 'POP_risk' in result.columns
        assert 'NR_risk' in result.columns
        assert 'Dusky_risk' in result.columns
        assert result.iloc[0]['POP_risk'] == 'critical'
        assert result.iloc[0]['NR_risk'] == 'warning'
        assert result.iloc[0]['Dusky_risk'] == 'ok'

    def test_vessel_at_risk_when_any_critical(self):
        """Should flag vessel at risk if any species is critical."""
        from app.views.dashboard import add_risk_flags

        df = pd.DataFrame({
            'llp': ['LLP1'],
            'POP_pct_remaining': [5.0],   # Critical
            'NR_pct_remaining': [75.0],   # OK
            'Dusky_pct_remaining': [75.0] # OK
        })

        result = add_risk_flags(df)

        assert result.iloc[0]['vessel_at_risk'] == True

    def test_vessel_not_at_risk_when_all_ok(self):
        """Should not flag vessel when all species OK."""
        from app.views.dashboard import add_risk_flags

        df = pd.DataFrame({
            'llp': ['LLP1'],
            'POP_pct_remaining': [75.0],
            'NR_pct_remaining': [80.0],
            'Dusky_pct_remaining': [90.0]
        })

        result = add_risk_flags(df)

        assert result.iloc[0]['vessel_at_risk'] == False

    def test_vessel_not_at_risk_when_only_warning(self):
        """Should not flag vessel when only warning level."""
        from app.views.dashboard import add_risk_flags

        df = pd.DataFrame({
            'llp': ['LLP1'],
            'POP_pct_remaining': [25.0],  # Warning
            'NR_pct_remaining': [30.0],   # Warning
            'Dusky_pct_remaining': [40.0] # Warning
        })

        result = add_risk_flags(df)

        assert result.iloc[0]['vessel_at_risk'] == False


class TestGetQuotaData:
    """Tests for get_quota_data function."""

    @patch('app.views.dashboard.supabase')
    def test_returns_empty_when_no_data(self, mock_supabase):
        """Should return empty DataFrame when no quota data."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        from app.views.dashboard import get_quota_data

        result = get_quota_data()

        assert result.empty

    @patch('app.views.dashboard.supabase')
    def test_joins_with_coop_members(self, mock_supabase):
        """Should join quota data with vessel info."""
        # Mock quota_remaining data
        quota_response = MagicMock()
        quota_response.data = [{
            'llp': 'LLP1',
            'species_code': 141,
            'remaining_lbs': 5000,
            'allocation_lbs': 10000
        }]

        # Mock coop_members data
        members_response = MagicMock()
        members_response.data = [{
            'llp': 'LLP1',
            'vessel_name': 'Test Vessel',
            'coop_code': 'SB'
        }]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == 'quota_remaining':
                mock_table.select.return_value.eq.return_value.execute.return_value = quota_response
            else:
                mock_table.select.return_value.execute.return_value = members_response
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        from app.views.dashboard import get_quota_data

        result = get_quota_data()

        assert 'vessel_name' in result.columns
        assert 'coop_code' in result.columns
        assert result.iloc[0]['vessel_name'] == 'Test Vessel'

    @patch('app.views.dashboard.supabase')
    def test_maps_species_codes(self, mock_supabase):
        """Should map species codes to names."""
        quota_response = MagicMock()
        quota_response.data = [
            {'llp': 'LLP1', 'species_code': 141, 'remaining_lbs': 5000, 'allocation_lbs': 10000},
            {'llp': 'LLP1', 'species_code': 136, 'remaining_lbs': 3000, 'allocation_lbs': 6000},
        ]

        members_response = MagicMock()
        members_response.data = [{'llp': 'LLP1', 'vessel_name': 'Test', 'coop_code': 'SB'}]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == 'quota_remaining':
                mock_table.select.return_value.eq.return_value.execute.return_value = quota_response
            else:
                mock_table.select.return_value.execute.return_value = members_response
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        from app.views.dashboard import get_quota_data

        result = get_quota_data()

        assert 'species' in result.columns
        species_list = result['species'].tolist()
        assert 'POP' in species_list
        assert 'NR' in species_list

    @patch('app.views.dashboard.supabase')
    def test_calculates_percent_remaining(self, mock_supabase):
        """Should calculate pct_remaining correctly."""
        quota_response = MagicMock()
        quota_response.data = [{
            'llp': 'LLP1',
            'species_code': 141,
            'remaining_lbs': 2500,
            'allocation_lbs': 10000
        }]

        members_response = MagicMock()
        members_response.data = [{'llp': 'LLP1', 'vessel_name': 'Test', 'coop_code': 'SB'}]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == 'quota_remaining':
                mock_table.select.return_value.eq.return_value.execute.return_value = quota_response
            else:
                mock_table.select.return_value.execute.return_value = members_response
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        from app.views.dashboard import get_quota_data

        result = get_quota_data()

        assert result.iloc[0]['pct_remaining'] == 25.0  # 2500/10000 * 100

    @patch('app.views.dashboard.supabase')
    def test_handles_zero_allocation(self, mock_supabase):
        """Should handle zero allocation without division error."""
        quota_response = MagicMock()
        quota_response.data = [{
            'llp': 'LLP1',
            'species_code': 141,
            'remaining_lbs': 0,
            'allocation_lbs': 0  # Zero allocation
        }]

        members_response = MagicMock()
        members_response.data = [{'llp': 'LLP1', 'vessel_name': 'Test', 'coop_code': 'SB'}]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == 'quota_remaining':
                mock_table.select.return_value.eq.return_value.execute.return_value = quota_response
            else:
                mock_table.select.return_value.execute.return_value = members_response
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        from app.views.dashboard import get_quota_data

        result = get_quota_data()

        assert result.iloc[0]['pct_remaining'] is None  # Should be None, not error


class TestKpiCard:
    """Tests for kpi_card function."""

    def test_generates_html(self):
        """Should generate HTML string."""
        from app.views.dashboard import kpi_card

        result = kpi_card("Test Label", "42")

        assert '<div' in result
        assert 'Test Label' in result
        assert '42' in result

    def test_includes_subtitle_when_provided(self):
        """Should include subtitle in HTML."""
        from app.views.dashboard import kpi_card

        result = kpi_card("Label", "100", subtitle="extra info")

        assert 'extra info' in result


class TestSpeciesKpiCard:
    """Tests for species_kpi_card function."""

    def test_includes_percentage(self):
        """Should include formatted percentage."""
        from app.views.dashboard import species_kpi_card

        result = species_kpi_card("POP", 75.5, 7500, 10000)

        assert '76%' in result  # Rounded

    def test_includes_remaining_and_allocated(self):
        """Should show remaining of allocated."""
        from app.views.dashboard import species_kpi_card

        result = species_kpi_card("NR", 50, 5000, 10000)

        assert '5.0K' in result
        assert '10.0K' in result

    def test_uses_correct_color_for_risk(self):
        """Should use red color for critical percentage."""
        from app.views.dashboard import species_kpi_card

        result = species_kpi_card("POP", 5, 500, 10000)

        assert '#dc2626' in result  # Red for critical


class TestEdgeCases:
    """Edge case tests for dashboard functionality."""

    def test_risk_level_exactly_10_percent(self):
        """Exactly 10% should be 'warning', not 'critical'."""
        from app.utils.formatting import get_risk_level

        result = get_risk_level(10.0)
        assert result == 'warning'

    def test_risk_level_exactly_50_percent(self):
        """Exactly 50% should be 'ok', not 'warning'."""
        from app.utils.formatting import get_risk_level

        result = get_risk_level(50.0)
        assert result == 'ok'

    def test_risk_level_just_under_10(self):
        """9.99% should still be 'critical'."""
        from app.utils.formatting import get_risk_level

        result = get_risk_level(9.99)
        assert result == 'critical'

    def test_risk_level_just_under_50(self):
        """49.99% should still be 'warning'."""
        from app.utils.formatting import get_risk_level

        result = get_risk_level(49.99)
        assert result == 'warning'

    def test_negative_percentage_is_critical(self):
        """Negative percentage (overdrawn) should be 'critical'."""
        from app.utils.formatting import get_risk_level

        result = get_risk_level(-10.0)
        assert result == 'critical'

    def test_negative_percentage_color(self):
        """Negative percentage should show red color."""
        from app.utils.formatting import get_pct_color

        result = get_pct_color(-25.0)
        assert result == '#dc2626'  # Red

    def test_format_lbs_negative(self):
        """Should format negative numbers correctly."""
        from app.utils.formatting import format_lbs

        # Negative thousands
        assert format_lbs(-5000) == '-5.0K'
        # Negative millions
        assert format_lbs(-1_000_000) == '-1.0M'

    def test_format_lbs_very_large(self):
        """Should handle very large numbers."""
        from app.utils.formatting import format_lbs

        result = format_lbs(999_999_999)
        assert 'M' in result

    def test_percentage_over_100(self):
        """Should handle >100% remaining (transfers in exceeded usage)."""
        from app.utils.formatting import get_risk_level, get_pct_color

        result_level = get_risk_level(150.0)
        result_color = get_pct_color(150.0)

        assert result_level == 'ok'
        assert result_color == '#059669'  # Green (standardized ok color)

    @patch('app.views.dashboard.supabase')
    def test_unknown_species_code_in_data(self, mock_supabase):
        """Should filter out species codes not in SPECIES_MAP."""
        quota_response = MagicMock()
        quota_response.data = [{
            'llp': 'LLP1',
            'species_code': 999,  # Unknown code
            'remaining_lbs': 5000,
            'allocation_lbs': 10000
        }]

        members_response = MagicMock()
        members_response.data = [{'llp': 'LLP1', 'vessel_name': 'Test', 'coop_code': 'SB'}]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == 'quota_remaining':
                mock_table.select.return_value.eq.return_value.execute.return_value = quota_response
            else:
                mock_table.select.return_value.execute.return_value = members_response
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        from app.views.dashboard import get_quota_data

        # Unknown species should be filtered out
        result = get_quota_data()
        assert len(result) == 0  # Row with unknown species filtered out

    @patch('app.views.dashboard.supabase')
    def test_mixed_known_and_unknown_species(self, mock_supabase):
        """Should keep known species and filter unknown ones."""
        quota_response = MagicMock()
        quota_response.data = [
            {'llp': 'LLP1', 'species_code': 141, 'remaining_lbs': 5000, 'allocation_lbs': 10000},  # POP - keep
            {'llp': 'LLP1', 'species_code': 999, 'remaining_lbs': 1000, 'allocation_lbs': 2000},   # Unknown - filter
            {'llp': 'LLP1', 'species_code': 136, 'remaining_lbs': 3000, 'allocation_lbs': 6000},   # NR - keep
        ]

        members_response = MagicMock()
        members_response.data = [{'llp': 'LLP1', 'vessel_name': 'Test', 'coop_code': 'SB'}]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == 'quota_remaining':
                mock_table.select.return_value.eq.return_value.execute.return_value = quota_response
            else:
                mock_table.select.return_value.execute.return_value = members_response
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        from app.views.dashboard import get_quota_data

        result = get_quota_data()

        # Should have 2 rows (POP and NR), not 3
        assert len(result) == 2
        assert set(result['species'].tolist()) == {'POP', 'NR'}

    def test_pivot_with_missing_species(self):
        """Should handle vessel with only some species data."""
        from app.views.dashboard import pivot_quota_data
        import pandas as pd

        df = pd.DataFrame({
            'llp': ['LLP1', 'LLP1'],  # Only 2 species, missing Dusky
            'vessel_name': ['Vessel 1', 'Vessel 1'],
            'coop_code': ['SB', 'SB'],
            'species': ['POP', 'NR'],
            'remaining_lbs': [5000, 3000],
            'allocation_lbs': [10000, 6000],
            'pct_remaining': [50.0, 50.0]
        })

        result = pivot_quota_data(df)

        assert len(result) == 1
        assert 'POP_remaining_lbs' in result.columns
        assert 'NR_remaining_lbs' in result.columns
        # Dusky columns should exist but be NaN
        if 'Dusky_remaining_lbs' in result.columns:
            assert pd.isna(result.iloc[0]['Dusky_remaining_lbs'])

    def test_add_risk_flags_with_nan_percentages(self):
        """Should handle NaN percentages in risk calculation."""
        from app.views.dashboard import add_risk_flags
        import pandas as pd
        import numpy as np

        df = pd.DataFrame({
            'llp': ['LLP1'],
            'POP_pct_remaining': [np.nan],
            'NR_pct_remaining': [50.0],
            'Dusky_pct_remaining': [75.0]
        })

        result = add_risk_flags(df)

        assert result.iloc[0]['POP_risk'] == 'na'
        assert result.iloc[0]['NR_risk'] == 'ok'
        assert result.iloc[0]['Dusky_risk'] == 'ok'
        # Vessel should not be at risk if NaN (unknown) rather than critical
        assert result.iloc[0]['vessel_at_risk'] == False

    def test_species_kpi_card_with_zero_allocation(self):
        """Should handle zero allocation gracefully."""
        from app.views.dashboard import species_kpi_card

        # Zero allocation - percentage should be handled
        result = species_kpi_card("POP", None, 0, 0)

        assert 'POP' in result
        assert 'N/A' in result  # Should display N/A for unknown percentage
        assert '#94a3b8' in result  # Gray color for N/A

    def test_species_kpi_card_with_negative_remaining(self):
        """Should display negative remaining (overdrawn)."""
        from app.views.dashboard import species_kpi_card

        result = species_kpi_card("POP", -10.0, -1000, 10000)

        assert 'POP' in result
        assert '#dc2626' in result  # Red for critical/negative
