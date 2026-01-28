"""Unit tests for multi-haul bycatch alert functionality."""

import pytest
from datetime import date, time
from unittest.mock import MagicMock, patch

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_rpca_areas():
    """Sample RPCA areas for testing."""
    return [
        {"id": 1, "code": "RPCA-1", "name": "Area 1"},
        {"id": 2, "code": "RPCA-2", "name": "Area 2"},
        {"id": 3, "code": "RPCA-3", "name": "Area 3"},
    ]


@pytest.fixture
def sample_haul_data():
    """Sample haul form data."""
    return {
        "haul_number": 1,
        "location_name": "Test Location",
        "high_salmon_encounter": False,
        "set_date": date(2026, 1, 15),
        "set_time": time(8, 30),
        "set_latitude": 57.5,
        "set_longitude": -152.3,
        "retrieval_date": date(2026, 1, 15),
        "retrieval_time": time(14, 0),
        "retrieval_latitude": 57.6,
        "retrieval_longitude": -152.4,
        "bottom_depth": 100,
        "sea_depth": 80,
        "rpca_area_id": 1,
        "amount": 500.0
    }


@pytest.fixture
def sample_multi_haul_data():
    """Sample multiple hauls for testing."""
    return [
        {
            "haul_number": 1,
            "location_name": "Tater",
            "high_salmon_encounter": False,
            "set_date": date(2026, 1, 15),
            "set_time": time(6, 0),
            "set_latitude": 57.5,
            "set_longitude": -152.3,
            "amount": 300.0
        },
        {
            "haul_number": 2,
            "location_name": "Shit Hole",
            "high_salmon_encounter": True,
            "set_date": date(2026, 1, 15),
            "set_time": time(10, 30),
            "set_latitude": 57.6,
            "set_longitude": -152.4,
            "amount": 200.0
        },
    ]


# =============================================================================
# HAUL VALIDATION TESTS
# =============================================================================

class TestHaulValidation:
    """Tests for haul data validation."""

    def test_validates_set_latitude_within_alaska_bounds(self):
        """Should accept set_latitude within Alaska bounds (50-72)."""
        from app.components.haul_form import validate_haul_data

        haul = {
            "set_latitude": 57.0,
            "set_longitude": -152.0,
            "set_date": date.today(),
            "amount": 100
        }
        valid, error = validate_haul_data(haul)

        assert valid is True
        assert error is None

    def test_rejects_set_latitude_below_alaska_bounds(self):
        """Should reject set_latitude below Alaska bounds."""
        from app.components.haul_form import validate_haul_data

        haul = {
            "set_latitude": 45.0,
            "set_longitude": -152.0,
            "set_date": date.today(),
            "amount": 100
        }
        valid, error = validate_haul_data(haul)

        assert valid is False
        assert "latitude" in error.lower()

    def test_rejects_set_latitude_above_alaska_bounds(self):
        """Should reject set_latitude above Alaska bounds."""
        from app.components.haul_form import validate_haul_data

        haul = {
            "set_latitude": 75.0,
            "set_longitude": -152.0,
            "set_date": date.today(),
            "amount": 100
        }
        valid, error = validate_haul_data(haul)

        assert valid is False
        assert "latitude" in error.lower()

    def test_rejects_set_longitude_outside_alaska_bounds(self):
        """Should reject set_longitude outside Alaska bounds."""
        from app.components.haul_form import validate_haul_data

        haul = {
            "set_latitude": 57.0,
            "set_longitude": -120.0,
            "set_date": date.today(),
            "amount": 100
        }
        valid, error = validate_haul_data(haul)

        assert valid is False
        assert "longitude" in error.lower()

    def test_rejects_non_positive_amount(self):
        """Should reject non-positive amounts."""
        from app.components.haul_form import validate_haul_data

        haul = {
            "set_latitude": 57.0,
            "set_longitude": -152.0,
            "set_date": date.today(),
            "amount": 0
        }
        valid, error = validate_haul_data(haul)

        assert valid is False
        assert "amount" in error.lower()

    def test_rejects_negative_amount(self):
        """Should reject negative amounts."""
        from app.components.haul_form import validate_haul_data

        haul = {
            "set_latitude": 57.0,
            "set_longitude": -152.0,
            "set_date": date.today(),
            "amount": -100
        }
        valid, error = validate_haul_data(haul)

        assert valid is False
        assert "amount" in error.lower()

    def test_accepts_null_retrieval_coordinates(self):
        """Should accept null retrieval coordinates (optional fields)."""
        from app.components.haul_form import validate_haul_data

        haul = {
            "set_latitude": 57.0,
            "set_longitude": -152.0,
            "set_date": date.today(),
            "amount": 100,
            "retrieval_latitude": None,
            "retrieval_longitude": None
        }
        valid, error = validate_haul_data(haul)

        assert valid is True

    def test_rejects_retrieval_latitude_outside_bounds(self):
        """Should reject retrieval_latitude outside Alaska bounds."""
        from app.components.haul_form import validate_haul_data

        haul = {
            "set_latitude": 57.0,
            "set_longitude": -152.0,
            "set_date": date.today(),
            "amount": 100,
            "retrieval_latitude": 45.0,
            "retrieval_longitude": -152.0
        }
        valid, error = validate_haul_data(haul)

        assert valid is False
        assert "retrieval latitude" in error.lower()

    def test_requires_set_date(self):
        """Should require set_date."""
        from app.components.haul_form import validate_haul_data

        haul = {
            "set_latitude": 57.0,
            "set_longitude": -152.0,
            "set_date": None,
            "amount": 100
        }
        valid, error = validate_haul_data(haul)

        assert valid is False
        assert "date" in error.lower()


# =============================================================================
# COORDINATE CONVERSION TESTS
# =============================================================================

class TestCoordinateConversion:
    """Tests for coordinate format conversions."""

    def test_dms_to_decimal_north_latitude(self):
        """Should correctly convert DMS to decimal for north latitude."""
        from app.utils.coordinates import dms_to_decimal

        # 57° 30.0' N = 57.5
        result = dms_to_decimal(57, 30.0, "N")
        assert abs(result - 57.5) < 0.001

    def test_dms_to_decimal_west_longitude(self):
        """Should correctly convert DMS to decimal for west longitude."""
        from app.utils.coordinates import dms_to_decimal

        # 152° 15.0' W = -152.25
        result = dms_to_decimal(152, 15.0, "W")
        assert abs(result - (-152.25)) < 0.001

    def test_decimal_to_dms_north_latitude(self):
        """Should correctly convert decimal to DMS for north latitude."""
        from app.utils.coordinates import decimal_to_dms

        degrees, minutes, direction = decimal_to_dms(57.5, is_latitude=True)
        assert degrees == 57
        assert abs(minutes - 30.0) < 0.1
        assert direction == "N"

    def test_decimal_to_dms_west_longitude(self):
        """Should correctly convert decimal to DMS for west longitude."""
        from app.utils.coordinates import decimal_to_dms

        degrees, minutes, direction = decimal_to_dms(-152.25, is_latitude=False)
        assert degrees == 152
        assert abs(minutes - 15.0) < 0.1
        assert direction == "W"

    def test_format_coordinates_dms(self):
        """Should format lat/lon pair as DMS string."""
        from app.utils.coordinates import format_coordinates_dms

        result = format_coordinates_dms(57.5, -152.25)
        assert "57" in result
        assert "152" in result
        assert "N" in result
        assert "W" in result


# =============================================================================
# METRIC TON CONVERSION TESTS
# =============================================================================

class TestMetricTonConversion:
    """Tests for metric ton conversion in transfers."""

    def test_format_with_mt(self):
        """Should format pounds with MT equivalent."""
        from app.views.transfers import format_with_mt, LBS_PER_MT

        result = format_with_mt(2204.62)
        assert "2,205" in result or "2205" in result  # Pounds rounded
        assert "1.00" in result  # MT should be 1.00

    def test_format_with_mt_large_value(self):
        """Should handle large values correctly."""
        from app.views.transfers import format_with_mt

        result = format_with_mt(22046.2)  # 10 MT
        assert "10.00" in result or "10" in result.split("(")[1]

    def test_lbs_per_mt_constant(self):
        """Should have correct LBS_PER_MT constant."""
        from app.views.transfers import LBS_PER_MT

        assert abs(LBS_PER_MT - 2204.62) < 0.01


# =============================================================================
# SPECIES OPTIONS TESTS
# =============================================================================

class TestSpeciesOptions:
    """Tests for species options in transfers."""

    def test_contains_original_target_species(self):
        """Should contain original target species (POP, NR, Dusky)."""
        from app.views.transfers import SPECIES_OPTIONS

        assert 141 in SPECIES_OPTIONS  # POP
        assert 136 in SPECIES_OPTIONS  # NR
        assert 172 in SPECIES_OPTIONS  # Dusky

    def test_contains_new_secondary_species(self):
        """Should contain new secondary species."""
        from app.views.transfers import SPECIES_OPTIONS

        assert 137 in SPECIES_OPTIONS  # Shortraker
        assert 138 in SPECIES_OPTIONS  # Rougheye
        assert 143 in SPECIES_OPTIONS  # Thornyhead

    def test_contains_halibut(self):
        """Should contain Halibut for transfers."""
        from app.views.transfers import SPECIES_OPTIONS

        assert 200 in SPECIES_OPTIONS  # Halibut

    def test_species_names_include_short_and_full_names(self):
        """Species display names should include both short and full names."""
        from app.views.transfers import SPECIES_OPTIONS

        assert "POP" in SPECIES_OPTIONS[141]
        assert "Pacific Ocean Perch" in SPECIES_OPTIONS[141]


# =============================================================================
# ALERT TOTAL AMOUNT TESTS
# =============================================================================

class TestAlertTotalAmount:
    """Tests for alert total amount calculation from hauls."""

    def test_sum_haul_amounts(self, sample_multi_haul_data):
        """Should correctly sum amounts from multiple hauls."""
        total = sum(h["amount"] for h in sample_multi_haul_data)
        assert total == 500.0  # 300 + 200

    def test_high_salmon_detection(self, sample_multi_haul_data):
        """Should detect high salmon encounter flag."""
        has_salmon = any(h.get("high_salmon_encounter") for h in sample_multi_haul_data)
        assert has_salmon is True

    def test_no_high_salmon_when_all_false(self, sample_haul_data):
        """Should return False when no hauls have high salmon."""
        hauls = [sample_haul_data]
        has_salmon = any(h.get("high_salmon_encounter") for h in hauls)
        assert has_salmon is False


# =============================================================================
# RPCA AREA TESTS
# =============================================================================

class TestRpcaAreas:
    """Tests for RPCA area functionality."""

    def test_rpca_lookup(self, sample_rpca_areas):
        """Should create correct lookup from RPCA areas."""
        lookup = {a["id"]: a["code"] for a in sample_rpca_areas}

        assert lookup[1] == "RPCA-1"
        assert lookup[2] == "RPCA-2"
        assert lookup[3] == "RPCA-3"

    def test_rpca_area_codes_format(self, sample_rpca_areas):
        """RPCA codes should follow RPCA-N format."""
        for area in sample_rpca_areas:
            assert area["code"].startswith("RPCA-")


# =============================================================================
# HAUL NUMBERING TESTS
# =============================================================================

class TestHaulNumbering:
    """Tests for haul auto-numbering."""

    def test_hauls_numbered_sequentially(self, sample_multi_haul_data):
        """Hauls should have sequential haul_number values."""
        numbers = [h["haul_number"] for h in sample_multi_haul_data]
        assert numbers == [1, 2]

    def test_haul_numbers_start_at_one(self, sample_haul_data):
        """First haul should have haul_number = 1."""
        assert sample_haul_data["haul_number"] == 1
