"""Database integration tests for quota tracking.

These tests verify the quota_remaining view calculates correctly
by inserting real data into the test database.

Run with: pytest tests/test_quota_tracking.py -v

Requirements:
    - SUPABASE_URL in .env
    - SUPABASE_SERVICE_ROLE_KEY in .env (bypasses RLS for test data)

To get the service role key:
    1. Go to Supabase dashboard → Settings → API
    2. Copy the 'service_role' key (NOT the anon key)
    3. Add to .env: SUPABASE_SERVICE_ROLE_KEY=your-key
"""

import pytest
import uuid
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# Import after load_dotenv so env vars are available
from supabase import create_client
import os

# Test constants
TEST_ORG_ID = "00000000-0000-0000-0000-000000000099"  # Dedicated test org
TEST_YEAR = 2099  # Far future year to avoid conflicts
TEST_LLP_A = "TEST_LLP_A"
TEST_LLP_B = "TEST_LLP_B"
SPECIES_POP = 141
SPECIES_NR = 136


@pytest.fixture(scope="module")
def supabase():
    """Create Supabase client for tests.

    Uses service role key to bypass RLS for test data insertion.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url:
        pytest.skip("SUPABASE_URL required for integration tests")

    if not key:
        pytest.skip(
            "SUPABASE_SERVICE_ROLE_KEY required for integration tests. "
            "Get it from Supabase dashboard → Settings → API → service_role key"
        )

    return create_client(url, key)


@pytest.fixture(scope="module")
def test_org(supabase):
    """Create test organization if it doesn't exist."""
    # Check if test org exists
    result = supabase.table("organizations").select("id").eq("id", TEST_ORG_ID).execute()

    if not result.data:
        # Create test org
        supabase.table("organizations").insert({
            "id": TEST_ORG_ID,
            "name": "Test Organization (DO NOT DELETE)",
            "slug": "test-org"
        }).execute()

    yield TEST_ORG_ID

    # Don't delete org - keep it for future test runs


@pytest.fixture(autouse=True)
def cleanup_test_data(supabase, test_org):
    """Clean up test data before and after each test."""
    def clean():
        # Delete test allocations
        supabase.table("vessel_allocations").delete().eq("org_id", TEST_ORG_ID).execute()
        # Delete test transfers
        supabase.table("quota_transfers").delete().eq("org_id", TEST_ORG_ID).execute()
        # Delete test harvests
        supabase.table("harvests").delete().eq("org_id", TEST_ORG_ID).execute()

    clean()  # Before test
    yield
    clean()  # After test


def get_quota_remaining(supabase, llp: str, species_code: int, year: int) -> dict | None:
    """Query quota_remaining view for a specific LLP/species/year."""
    result = supabase.table("quota_remaining").select("*").eq(
        "llp", llp
    ).eq(
        "species_code", species_code
    ).eq(
        "year", year
    ).execute()

    return result.data[0] if result.data else None


def insert_allocation(supabase, org_id: str, llp: str, species_code: int, year: int, pounds: float):
    """Insert a vessel allocation."""
    supabase.table("vessel_allocations").insert({
        "org_id": org_id,
        "llp": llp,
        "species_code": species_code,
        "year": year,
        "allocation_lbs": pounds
    }).execute()


def insert_transfer(supabase, org_id: str, from_llp: str, to_llp: str,
                    species_code: int, year: int, pounds: float, is_deleted: bool = False):
    """Insert a quota transfer."""
    supabase.table("quota_transfers").insert({
        "org_id": org_id,
        "from_llp": from_llp,
        "to_llp": to_llp,
        "species_code": species_code,
        "year": year,
        "pounds": pounds,
        "transfer_date": date.today().isoformat(),
        "is_deleted": is_deleted
    }).execute()


def insert_harvest(supabase, org_id: str, llp: str, species_code: int,
                   harvest_date: date, pounds: float, is_deleted: bool = False):
    """Insert a harvest record."""
    supabase.table("harvests").insert({
        "org_id": org_id,
        "llp": llp,
        "species_code": species_code,
        "harvest_date": harvest_date.isoformat(),
        "pounds": pounds,
        "is_deleted": is_deleted
    }).execute()


class TestQuotaAllocation:
    """Tests for basic allocation display."""

    def test_allocation_only_shows_full_remaining(self, supabase, test_org):
        """Fresh allocation with no transfers/harvests should show full amount."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        assert quota is not None
        assert quota["allocation_lbs"] == 50000
        assert quota["transfers_in"] == 0
        assert quota["transfers_out"] == 0
        assert quota["harvested"] == 0
        assert quota["remaining_lbs"] == 50000

    def test_zero_allocation(self, supabase, test_org):
        """Zero allocation should show zero remaining."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 0)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        assert quota is not None
        assert quota["remaining_lbs"] == 0


class TestQuotaTransfers:
    """Tests for transfer effects on quota."""

    def test_transfer_out_reduces_source_quota(self, supabase, test_org):
        """Outbound transfer should reduce source LLP's remaining quota."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 30000)
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 10000)

        # Act
        quota_a = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        assert quota_a["allocation_lbs"] == 50000
        assert quota_a["transfers_out"] == 10000
        assert quota_a["remaining_lbs"] == 40000  # 50000 - 10000

    def test_transfer_in_increases_dest_quota(self, supabase, test_org):
        """Inbound transfer should increase destination LLP's remaining quota."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 30000)
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 10000)

        # Act
        quota_b = get_quota_remaining(supabase, TEST_LLP_B, SPECIES_POP, TEST_YEAR)

        # Assert
        assert quota_b["allocation_lbs"] == 30000
        assert quota_b["transfers_in"] == 10000
        assert quota_b["remaining_lbs"] == 40000  # 30000 + 10000

    def test_multiple_transfers_accumulate(self, supabase, test_org):
        """Multiple transfers should sum correctly."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 30000)

        # Three transfers: A -> B
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 5000)
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 3000)
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 2000)

        # Act
        quota_a = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)
        quota_b = get_quota_remaining(supabase, TEST_LLP_B, SPECIES_POP, TEST_YEAR)

        # Assert
        assert quota_a["transfers_out"] == 10000  # 5000 + 3000 + 2000
        assert quota_a["remaining_lbs"] == 40000  # 50000 - 10000
        assert quota_b["transfers_in"] == 10000
        assert quota_b["remaining_lbs"] == 40000  # 30000 + 10000

    def test_soft_deleted_transfer_excluded(self, supabase, test_org):
        """Soft-deleted transfers should not affect quota."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 30000)

        # Active transfer
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 5000, is_deleted=False)
        # Deleted transfer - should be ignored
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 10000, is_deleted=True)

        # Act
        quota_a = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert - only the 5000 transfer should count
        assert quota_a["transfers_out"] == 5000
        assert quota_a["remaining_lbs"] == 45000  # 50000 - 5000


class TestQuotaHarvests:
    """Tests for harvest effects on quota."""

    def test_harvest_reduces_quota(self, supabase, test_org):
        """Harvest should reduce remaining quota."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 15), 15000)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        assert quota["harvested"] == 15000
        assert quota["remaining_lbs"] == 35000  # 50000 - 15000

    def test_multiple_harvests_accumulate(self, supabase, test_org):
        """Multiple harvests should sum correctly."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)

        # Five deliveries
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 1), 5000)
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 10), 8000)
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 20), 3000)
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 7, 5), 4000)
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 7, 15), 5000)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        assert quota["harvested"] == 25000  # 5000 + 8000 + 3000 + 4000 + 5000
        assert quota["remaining_lbs"] == 25000  # 50000 - 25000

    def test_soft_deleted_harvest_excluded(self, supabase, test_org):
        """Soft-deleted harvests should not affect quota."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)

        # Active harvest
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 1), 10000, is_deleted=False)
        # Deleted harvest - should be ignored
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 10), 20000, is_deleted=True)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert - only the 10000 harvest should count
        assert quota["harvested"] == 10000
        assert quota["remaining_lbs"] == 40000  # 50000 - 10000


class TestQuotaIsolation:
    """Tests for species and year isolation."""

    def test_species_isolation(self, supabase, test_org):
        """Transfers for one species should not affect another species."""
        # Arrange - allocations for both POP and NR
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_NR, TEST_YEAR, 30000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 20000)

        # Transfer POP only
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 10000)

        # Act
        quota_pop = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)
        quota_nr = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_NR, TEST_YEAR)

        # Assert - NR should be unaffected
        assert quota_pop["remaining_lbs"] == 40000  # 50000 - 10000 transfer
        assert quota_nr["remaining_lbs"] == 30000   # Unchanged

    def test_year_isolation(self, supabase, test_org):
        """Activity in one year should not affect another year."""
        # Arrange - allocations for two years
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR - 1, 45000)

        # Harvest in TEST_YEAR only
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 15), 20000)

        # Act
        quota_current = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)
        quota_prior = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR - 1)

        # Assert - prior year should be unaffected
        assert quota_current["remaining_lbs"] == 30000  # 50000 - 20000
        assert quota_prior["remaining_lbs"] == 45000    # Unchanged


class TestQuotaEdgeCases:
    """Edge case tests for quota tracking."""

    def test_full_quota_formula(self, supabase, test_org):
        """Test the complete formula: allocation + in - out - harvested."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 30000)

        # A receives 5000 from B
        insert_transfer(supabase, test_org, TEST_LLP_B, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 5000)
        # A sends 3000 to B
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 3000)
        # A harvests 20000
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 15), 20000)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        # remaining = 50000 + 5000 - 3000 - 20000 = 32000
        assert quota["allocation_lbs"] == 50000
        assert quota["transfers_in"] == 5000
        assert quota["transfers_out"] == 3000
        assert quota["harvested"] == 20000
        assert quota["remaining_lbs"] == 32000

    def test_zero_remaining_after_full_harvest(self, supabase, test_org):
        """Harvesting exactly the allocation should result in zero remaining."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 25000)
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 15), 25000)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        assert quota["remaining_lbs"] == 0

    def test_negative_remaining_overage(self, supabase, test_org):
        """Harvesting more than allocation should show negative remaining (overage)."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 25000)
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 15), 30000)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert - system should handle negative values
        assert quota["remaining_lbs"] == -5000

    def test_decimal_precision(self, supabase, test_org):
        """Decimal values should be handled correctly."""
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 10000.50)
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 15), 5000.25)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        assert float(quota["remaining_lbs"]) == pytest.approx(5000.25, rel=1e-2)
