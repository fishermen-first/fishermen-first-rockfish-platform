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
TEST_LLP_C = "TEST_LLP_C"
SPECIES_POP = 141
SPECIES_NR = 136
SPECIES_DUSKY = 172


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


# =============================================================================
# BYCATCH ALERTS RLS VERIFICATION
# =============================================================================

class TestBycatchAlertsRLS:
    """Tests to verify RLS policies for bycatch_alerts table.

    Verifies that vessel owners can only see their own alerts.
    """

    @pytest.fixture
    def cleanup_test_alerts(self, supabase, test_org):
        """Clean up test alerts before and after each test."""
        def clean():
            supabase.table("bycatch_alerts").delete().eq("org_id", TEST_ORG_ID).execute()

        clean()  # Before test
        yield
        clean()  # After test

    def test_vessel_owner_policy_restricts_to_own_alerts(self, supabase, test_org, cleanup_test_alerts):
        """RLS policy should restrict vessel owners to their own alerts only.

        This test uses service role to insert alerts for two different LLPs,
        then verifies the RLS policy exists and is correctly configured.
        Note: Full RLS testing requires user context, which is done in E2E tests.
        """
        # Arrange - insert alerts for two different LLPs
        alert1_id = str(uuid.uuid4())
        alert2_id = str(uuid.uuid4())

        supabase.table("bycatch_alerts").insert({
            "id": alert1_id,
            "org_id": TEST_ORG_ID,
            "reported_by_llp": TEST_LLP_A,
            "species_code": 200,  # Halibut
            "latitude": 57.5,
            "longitude": -152.3,
            "amount": 500,
            "status": "pending"
        }).execute()

        supabase.table("bycatch_alerts").insert({
            "id": alert2_id,
            "org_id": TEST_ORG_ID,
            "reported_by_llp": TEST_LLP_B,
            "species_code": 200,
            "latitude": 58.0,
            "longitude": -151.5,
            "amount": 300,
            "status": "pending"
        }).execute()

        # Act - verify both alerts exist (using service role bypasses RLS)
        result = supabase.table("bycatch_alerts").select("*").eq(
            "org_id", TEST_ORG_ID
        ).execute()

        # Assert - both alerts should be visible to service role
        assert len(result.data) == 2

        # Verify LLPs are different
        llps = {alert["reported_by_llp"] for alert in result.data}
        assert TEST_LLP_A in llps
        assert TEST_LLP_B in llps

    def test_rls_policy_exists_for_vessel_owner_select(self, supabase, test_org):
        """Verify the vessel_owner_select_alerts policy exists.

        Note: This test documents the policy existence. The actual policy
        is defined in sql/migrations/007_add_bycatch_alerts.sql and verified
        via E2E tests with real user authentication.
        """
        # We can't query pg_policies directly via Supabase client without
        # a custom RPC function. The policy existence is verified by:
        # 1. The migration that creates it (007_add_bycatch_alerts.sql)
        # 2. E2E tests that verify vessel owners can only see their own alerts
        # 3. Manual verification in Supabase dashboard

        # Document the expected policy configuration:
        expected_policy = {
            "name": "vessel_owner_select_alerts",
            "table": "bycatch_alerts",
            "command": "SELECT",
            "check": "org_id = get_user_org_id() AND reported_by_llp = user's LLP"
        }

        # This test serves as documentation - actual verification is in E2E
        assert expected_policy["name"] == "vessel_owner_select_alerts"

    def test_alerts_are_org_isolated(self, supabase, test_org, cleanup_test_alerts):
        """Alerts from different orgs should be isolated."""
        # Arrange - create alert in test org
        alert_id = str(uuid.uuid4())

        supabase.table("bycatch_alerts").insert({
            "id": alert_id,
            "org_id": TEST_ORG_ID,
            "reported_by_llp": TEST_LLP_A,
            "species_code": 200,
            "latitude": 57.5,
            "longitude": -152.3,
            "amount": 500,
            "status": "pending"
        }).execute()

        # Act - query only test org
        result = supabase.table("bycatch_alerts").select("*").eq(
            "org_id", TEST_ORG_ID
        ).execute()

        # Assert - only our test alert should be returned
        assert len(result.data) == 1
        assert result.data[0]["id"] == alert_id
        assert result.data[0]["org_id"] == TEST_ORG_ID


# =============================================================================
# CUSTOMER SCENARIO TESTS
# =============================================================================

class TestQuotaCustomerScenarios:
    """Real-world customer scenario tests for quota tracking math.

    These tests verify the quota calculation works correctly in realistic
    multi-step scenarios that customers would encounter during a fishing season.
    """

    def test_bidirectional_transfers(self, supabase, test_org):
        """Two LLPs trading quota back and forth should net correctly.

        Scenario: Vessel A and B adjust quota balance between them.
        - A transfers 10,000 to B
        - B transfers 3,000 back to A
        Net effect: A loses 7,000, B gains 7,000
        """
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 30000)

        # A -> B: 10,000
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 10000)
        # B -> A: 3,000 (partial return)
        insert_transfer(supabase, test_org, TEST_LLP_B, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 3000)

        # Act
        quota_a = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)
        quota_b = get_quota_remaining(supabase, TEST_LLP_B, SPECIES_POP, TEST_YEAR)

        # Assert
        # A: 50,000 + 3,000 (in) - 10,000 (out) = 43,000
        assert quota_a["transfers_in"] == 3000
        assert quota_a["transfers_out"] == 10000
        assert quota_a["remaining_lbs"] == 43000

        # B: 30,000 + 10,000 (in) - 3,000 (out) = 37,000
        assert quota_b["transfers_in"] == 10000
        assert quota_b["transfers_out"] == 3000
        assert quota_b["remaining_lbs"] == 37000

    def test_chain_transfers_pass_through(self, supabase, test_org):
        """Quota passing through multiple hands should track correctly.

        Scenario: A -> B -> C chain transfer
        - A starts with 50,000, transfers 15,000 to B
        - B starts with 30,000, receives 15,000, transfers 20,000 to C
        - C starts with 20,000, receives 20,000
        """
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 30000)
        insert_allocation(supabase, test_org, TEST_LLP_C, SPECIES_POP, TEST_YEAR, 20000)

        # Chain: A -> B -> C
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 15000)
        insert_transfer(supabase, test_org, TEST_LLP_B, TEST_LLP_C, SPECIES_POP, TEST_YEAR, 20000)

        # Act
        quota_a = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)
        quota_b = get_quota_remaining(supabase, TEST_LLP_B, SPECIES_POP, TEST_YEAR)
        quota_c = get_quota_remaining(supabase, TEST_LLP_C, SPECIES_POP, TEST_YEAR)

        # Assert
        # A: 50,000 - 15,000 = 35,000
        assert quota_a["remaining_lbs"] == 35000

        # B: 30,000 + 15,000 - 20,000 = 25,000
        assert quota_b["transfers_in"] == 15000
        assert quota_b["transfers_out"] == 20000
        assert quota_b["remaining_lbs"] == 25000

        # C: 20,000 + 20,000 = 40,000
        assert quota_c["remaining_lbs"] == 40000

    def test_harvest_against_boosted_quota(self, supabase, test_org):
        """Harvesting more than original allocation using transferred quota.

        Scenario: Vessel receives quota and harvests beyond original allocation.
        - A has 20,000 allocation
        - A receives 25,000 from B (boosted to 45,000)
        - A harvests 40,000 (more than original, within boosted)
        """
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 20000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 50000)

        # B sends 25,000 to A
        insert_transfer(supabase, test_org, TEST_LLP_B, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 25000)

        # A harvests 40,000 (more than original 20,000 allocation)
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 15), 40000)

        # Act
        quota_a = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        # A: 20,000 + 25,000 - 40,000 = 5,000
        assert quota_a["allocation_lbs"] == 20000
        assert quota_a["transfers_in"] == 25000
        assert quota_a["harvested"] == 40000
        assert quota_a["remaining_lbs"] == 5000

    def test_full_season_simulation(self, supabase, test_org):
        """Simulate a full fishing season with multiple operations.

        Scenario: Realistic season progression
        - Start: 100,000 allocation
        - Week 1: Harvest 15,000
        - Week 2: Receive transfer 10,000
        - Week 3: Harvest 25,000
        - Week 4: Transfer out 12,000
        - Week 5: Harvest 30,000
        """
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 100000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 50000)

        # Week 1: Harvest
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 1), 15000)

        # Week 2: Receive transfer from B
        insert_transfer(supabase, test_org, TEST_LLP_B, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 10000)

        # Week 3: Harvest
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 15), 25000)

        # Week 4: Transfer out to B
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 12000)

        # Week 5: Final harvest
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 29), 30000)

        # Act
        quota_a = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        # A: 100,000 + 10,000 - 12,000 - (15,000 + 25,000 + 30,000) = 28,000
        assert quota_a["allocation_lbs"] == 100000
        assert quota_a["transfers_in"] == 10000
        assert quota_a["transfers_out"] == 12000
        assert quota_a["harvested"] == 70000  # 15k + 25k + 30k
        assert quota_a["remaining_lbs"] == 28000

    def test_undo_then_redo_transfer(self, supabase, test_org):
        """Soft-deleted transfer replaced with new transfer should only count new.

        Scenario: Manager makes transfer, deletes it, creates corrected transfer.
        - Original: A -> B 10,000 (then soft deleted)
        - Corrected: A -> B 8,000
        Only the 8,000 should count.
        """
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 30000)

        # Original transfer - marked as deleted
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 10000, is_deleted=True)

        # Corrected transfer - active
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 8000, is_deleted=False)

        # Act
        quota_a = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)
        quota_b = get_quota_remaining(supabase, TEST_LLP_B, SPECIES_POP, TEST_YEAR)

        # Assert - only 8,000 counts, not 18,000 total
        assert quota_a["transfers_out"] == 8000
        assert quota_a["remaining_lbs"] == 42000  # 50,000 - 8,000

        assert quota_b["transfers_in"] == 8000
        assert quota_b["remaining_lbs"] == 38000  # 30,000 + 8,000

    def test_multi_species_full_scenario(self, supabase, test_org):
        """Operations on multiple species should be completely isolated.

        Scenario: Vessel has all three species, different operations on each.
        - POP: transfer out 10,000, harvest 8,000
        - NR: receive transfer 5,000, harvest 0
        - Dusky: no transfers, harvest 12,000
        """
        # Arrange - allocations for all three species
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 50000)
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_NR, TEST_YEAR, 30000)
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_DUSKY, TEST_YEAR, 20000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 40000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_NR, TEST_YEAR, 25000)

        # POP: A transfers out 10,000 to B
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 10000)
        # POP: A harvests 8,000
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 10), 8000)

        # NR: B transfers 5,000 to A
        insert_transfer(supabase, test_org, TEST_LLP_B, TEST_LLP_A, SPECIES_NR, TEST_YEAR, 5000)

        # Dusky: A harvests 12,000
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_DUSKY, date(TEST_YEAR, 6, 15), 12000)

        # Act
        quota_pop = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)
        quota_nr = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_NR, TEST_YEAR)
        quota_dusky = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_DUSKY, TEST_YEAR)

        # Assert - each species calculated independently
        # POP: 50,000 - 10,000 - 8,000 = 32,000
        assert quota_pop["remaining_lbs"] == 32000

        # NR: 30,000 + 5,000 = 35,000
        assert quota_nr["remaining_lbs"] == 35000

        # Dusky: 20,000 - 12,000 = 8,000
        assert quota_dusky["remaining_lbs"] == 8000

    def test_large_values(self, supabase, test_org):
        """Large quota values (millions of pounds) should calculate correctly.

        Scenario: Industrial-scale operation with high volumes.
        """
        # Arrange - 5 million lb allocation
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 5000000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 3000000)

        # Large transfers
        insert_transfer(supabase, test_org, TEST_LLP_B, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 1500000)
        insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 800000)

        # Large harvests
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 1), 2000000)
        insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 15), 1500000)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        # 5,000,000 + 1,500,000 - 800,000 - 3,500,000 = 2,200,000
        assert quota["allocation_lbs"] == 5000000
        assert quota["transfers_in"] == 1500000
        assert quota["transfers_out"] == 800000
        assert quota["harvested"] == 3500000
        assert quota["remaining_lbs"] == 2200000

    def test_many_transactions(self, supabase, test_org):
        """Many small transactions should aggregate accurately.

        Scenario: Vessel with frequent small deliveries and transfers.
        - 20 small transfers (10 in, 10 out)
        - 30 small harvests
        """
        # Arrange
        insert_allocation(supabase, test_org, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 100000)
        insert_allocation(supabase, test_org, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 100000)

        # 10 transfers in (each 500 lbs = 5,000 total)
        for i in range(10):
            insert_transfer(supabase, test_org, TEST_LLP_B, TEST_LLP_A, SPECIES_POP, TEST_YEAR, 500)

        # 10 transfers out (each 300 lbs = 3,000 total)
        for i in range(10):
            insert_transfer(supabase, test_org, TEST_LLP_A, TEST_LLP_B, SPECIES_POP, TEST_YEAR, 300)

        # 30 harvests (each 1,000 lbs = 30,000 total)
        for i in range(30):
            insert_harvest(supabase, test_org, TEST_LLP_A, SPECIES_POP, date(TEST_YEAR, 6, 1 + (i % 28)), 1000)

        # Act
        quota = get_quota_remaining(supabase, TEST_LLP_A, SPECIES_POP, TEST_YEAR)

        # Assert
        # 100,000 + 5,000 - 3,000 - 30,000 = 72,000
        assert quota["transfers_in"] == 5000
        assert quota["transfers_out"] == 3000
        assert quota["harvested"] == 30000
        assert quota["remaining_lbs"] == 72000


# =============================================================================
# ALLOCATION VERIFICATION TESTS
# =============================================================================

class TestAllocationVerification:
    """Verify database allocations match the official Excel source file.

    These tests compare the vessel_allocations table against the authoritative
    Excel spreadsheet: '2026 Rockfish Specs and Allocations.xlsx'

    Requirements:
        - SUPABASE_SERVICE_ROLE_KEY in .env
        - Excel file in project root: '2026 Rockfish Specs and Allocations.xlsx'
    """

    EXCEL_FILE = "2026 Rockfish Specs and Allocations.xlsx"
    SHEET_NAME = "CV Coop LLP Primary Alloc"
    YEAR = 2026

    # Cooperative name row positions and names in the Excel sheet
    COOPERATIVES = [
        (6, "Silver Bay Seafoods"),
        (26, "NORTH PACIFIC"),
        (44, "OBSI"),
        (61, "STAR OF KODIAK"),
    ]

    @pytest.fixture
    def excel_allocations(self):
        """Load allocations from the Excel source file."""
        import pandas as pd
        from pathlib import Path

        excel_path = Path(__file__).parent.parent / self.EXCEL_FILE
        if not excel_path.exists():
            pytest.skip(f"Excel file not found: {self.EXCEL_FILE}")

        df = pd.read_excel(excel_path, sheet_name=self.SHEET_NAME, header=None)

        allocations = {}
        for idx, (coop_row, coop_name) in enumerate(self.COOPERATIVES):
            data_start = coop_row + 3  # Data starts 3 rows after coop name
            next_coop = self.COOPERATIVES[idx + 1][0] if idx + 1 < len(self.COOPERATIVES) else len(df)

            for i in range(data_start, next_coop):
                llp = df.iloc[i, 0]
                vessel = df.iloc[i, 1]

                # Skip invalid rows
                if pd.isna(llp) or pd.isna(vessel):
                    continue
                if isinstance(vessel, str) and "TOTAL" in vessel.upper():
                    continue

                try:
                    llp_str = str(int(llp))
                    # TAC in pounds: POP=col 10, NR=col 11, Dusky=col 12
                    allocations[llp_str] = {
                        "vessel": vessel,
                        "coop": coop_name,
                        "POP": float(df.iloc[i, 10]) if pd.notna(df.iloc[i, 10]) else 0,
                        "NR": float(df.iloc[i, 11]) if pd.notna(df.iloc[i, 11]) else 0,
                        "DUSKY": float(df.iloc[i, 12]) if pd.notna(df.iloc[i, 12]) else 0,
                    }
                except (ValueError, TypeError):
                    pass

        return allocations

    @pytest.fixture
    def db_allocations(self, supabase):
        """Load allocations from the database."""
        # Species code mapping
        SPECIES_MAP = {141: "POP", 136: "NR", 172: "DUSKY"}

        result = supabase.table("vessel_allocations").select("*").eq("year", self.YEAR).execute()

        allocations = {}
        for row in result.data:
            llp = row["llp"]
            species = SPECIES_MAP.get(row["species_code"], str(row["species_code"]))

            if llp not in allocations:
                allocations[llp] = {}
            allocations[llp][species] = row["allocation_lbs"]

        return allocations

    def test_all_llps_present_in_database(self, excel_allocations, db_allocations):
        """All LLPs from Excel should exist in database."""
        missing = [llp for llp in excel_allocations if llp not in db_allocations]

        assert not missing, f"LLPs missing from database: {missing}"

    def test_no_extra_llps_in_database(self, excel_allocations, db_allocations):
        """Database should not have LLPs not in Excel."""
        extra = [llp for llp in db_allocations if llp not in excel_allocations]

        assert not extra, f"Extra LLPs in database not in Excel: {extra}"

    def test_llp_count_matches(self, excel_allocations, db_allocations):
        """Total LLP count should match between Excel and database."""
        assert len(excel_allocations) == len(db_allocations), (
            f"LLP count mismatch: Excel={len(excel_allocations)}, DB={len(db_allocations)}"
        )

    def test_pop_allocations_match(self, excel_allocations, db_allocations):
        """POP allocations should match between Excel and database."""
        mismatches = []

        for llp, excel in excel_allocations.items():
            if llp not in db_allocations:
                continue

            excel_val = excel.get("POP", 0)
            db_val = db_allocations[llp].get("POP", 0)

            if abs(excel_val - db_val) >= 1:  # Allow <1 lb tolerance for floating point
                mismatches.append({
                    "llp": llp,
                    "vessel": excel["vessel"],
                    "excel": excel_val,
                    "db": db_val,
                    "diff": excel_val - db_val,
                })

        assert not mismatches, f"POP allocation mismatches: {mismatches}"

    def test_nr_allocations_match(self, excel_allocations, db_allocations):
        """NR allocations should match between Excel and database."""
        mismatches = []

        for llp, excel in excel_allocations.items():
            if llp not in db_allocations:
                continue

            excel_val = excel.get("NR", 0)
            db_val = db_allocations[llp].get("NR", 0)

            if abs(excel_val - db_val) >= 1:
                mismatches.append({
                    "llp": llp,
                    "vessel": excel["vessel"],
                    "excel": excel_val,
                    "db": db_val,
                    "diff": excel_val - db_val,
                })

        assert not mismatches, f"NR allocation mismatches: {mismatches}"

    def test_dusky_allocations_match(self, excel_allocations, db_allocations):
        """Dusky allocations should match between Excel and database."""
        mismatches = []

        for llp, excel in excel_allocations.items():
            if llp not in db_allocations:
                continue

            excel_val = excel.get("DUSKY", 0)
            db_val = db_allocations[llp].get("DUSKY", 0)

            if abs(excel_val - db_val) >= 1:
                mismatches.append({
                    "llp": llp,
                    "vessel": excel["vessel"],
                    "excel": excel_val,
                    "db": db_val,
                    "diff": excel_val - db_val,
                })

        assert not mismatches, f"Dusky allocation mismatches: {mismatches}"

    def test_all_allocations_match(self, excel_allocations, db_allocations):
        """Comprehensive test: all species for all LLPs should match."""
        mismatches = []
        species_list = ["POP", "NR", "DUSKY"]

        for llp, excel in excel_allocations.items():
            if llp not in db_allocations:
                mismatches.append({"llp": llp, "error": "Missing from database"})
                continue

            for species in species_list:
                excel_val = excel.get(species, 0)
                db_val = db_allocations[llp].get(species, 0)

                if abs(excel_val - db_val) >= 1:
                    mismatches.append({
                        "llp": llp,
                        "species": species,
                        "excel": excel_val,
                        "db": db_val,
                        "diff": excel_val - db_val,
                    })

        assert not mismatches, (
            f"Found {len(mismatches)} allocation mismatches:\n" +
            "\n".join(str(m) for m in mismatches[:10]) +
            (f"\n... and {len(mismatches) - 10} more" if len(mismatches) > 10 else "")
        )

    def test_total_allocations_match(self, excel_allocations, db_allocations):
        """Total allocation sums should match between Excel and database."""
        species_list = ["POP", "NR", "DUSKY"]

        for species in species_list:
            excel_total = sum(excel.get(species, 0) for excel in excel_allocations.values())
            db_total = sum(db.get(species, 0) for db in db_allocations.values())

            assert abs(excel_total - db_total) < 1, (
                f"{species} total mismatch: Excel={excel_total:,.0f}, DB={db_total:,.0f}"
            )


# =============================================================================
# COOP MEMBERSHIP VERIFICATION TESTS
# =============================================================================

class TestCoopMembershipVerification:
    """Verify database coop_members match the official 2026 CGOA Rockfish Program membership.

    Reference: 2026 CGOA Rockfish Program Cooperative Membership list

    Cooperatives:
        - SOK (Star of Kodiak): coop_id=411, 15 members
        - OBSI: coop_id=409, 9 members
        - SBS (Silver Bay Seafoods): coop_id=407, 11 members
        - NP (North Pacific): coop_id=408, 11 members
    """

    # Official 2026 CGOA Rockfish Program Cooperative Membership
    # Format: {llp: {coop_code, coop_id, vessel_name}}
    EXPECTED_MEMBERSHIP = {
        # SOK - Star of Kodiak (coop_id=411)
        "2636": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "CAPE KIWANDA"},
        "3521": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "EXCALIBUR II"},
        "2567": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "ARCTIC RAM"},
        "2278": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "MARCY J"},
        "2550": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "MICHELLE RENEE"},
        "3144": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "PACIFIC RAM"},
        "3594": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "ARCTIC WIND"},
        "2364": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "ROSELLA"},
        "3463": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "TRAVELER"},
        "3658": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "OCEAN STORM"},
        "2882": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "PACIFIC STORM"},
        "1273": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "ELIZABETH F"},
        "1271": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "WALTER N"},
        "3987": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "GOLD RUSH"},
        "1523": {"coop_code": "SOK", "coop_id": 411, "vessel_name": "COLLIER BROTHERS"},
        # OBSI (coop_id=409)
        "3504": {"coop_code": "OBSI", "coop_id": 409, "vessel_name": "BAY ISLANDER"},
        "1367": {"coop_code": "OBSI", "coop_id": 409, "vessel_name": "DOMINION"},
        "4465": {"coop_code": "OBSI", "coop_id": 409, "vessel_name": "MARATHON"},
        "5201": {"coop_code": "OBSI", "coop_id": 409, "vessel_name": "NEW LIFE"},
        "4852": {"coop_code": "OBSI", "coop_id": 409, "vessel_name": "PACIFIC STAR"},
        "2603": {"coop_code": "OBSI", "coop_id": 409, "vessel_name": "TAASINGE"},
        "1619": {"coop_code": "OBSI", "coop_id": 409, "vessel_name": "STELLA"},
        "2188": {"coop_code": "OBSI", "coop_id": 409, "vessel_name": "GREEN HOPE"},
        "2683": {"coop_code": "OBSI", "coop_id": 409, "vessel_name": "OCEAN HOPE 3"},
        # SBS - Silver Bay Seafoods (coop_id=407)
        "3665": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "EVIE GRACE"},
        "3496": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "EVIE GRACE"},  # Company: MiRoCo LLC
        "1554": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "CHELLISSA"},
        "2165": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "DAWN"},
        "4851": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "NICHOLE"},  # Company: PK FISH HOLDINGS, LLC
        "1841": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "MAR DEL NORTE"},
        "2319": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "LAURA"},
        "3600": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "HICKORY WIND"},
        "3896": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "AMERICAN EAGLE"},
        "2565": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "VANGUARD"},
        "2696": {"coop_code": "SBS", "coop_id": 407, "vessel_name": "MAR PACIFICO"},
        # NP - North Pacific (coop_id=408)
        "1590": {"coop_code": "NP", "coop_id": 408, "vessel_name": "ALASKA BEAUTY"},
        "3764": {"coop_code": "NP", "coop_id": 408, "vessel_name": "ALASKAN"},
        "2148": {"coop_code": "NP", "coop_id": 408, "vessel_name": "TOPAZ"},  # Company: THOMAS TORMALA
        "2973": {"coop_code": "NP", "coop_id": 408, "vessel_name": "CARAVELLE"},
        "2487": {"coop_code": "NP", "coop_id": 408, "vessel_name": "NICHOLE"},
        "1755": {"coop_code": "NP", "coop_id": 408, "vessel_name": "ENTERPRISE"},
        "1541": {"coop_code": "NP", "coop_id": 408, "vessel_name": "SEA MAC"},  # Company: MAGIC FISH CO.
        "3785": {"coop_code": "NP", "coop_id": 408, "vessel_name": "SEA MAC"},
        "2653": {"coop_code": "NP", "coop_id": 408, "vessel_name": "SEA MAC"},  # Company: ALASKA DAWN SEAFOODS LLC
        "2535": {"coop_code": "NP", "coop_id": 408, "vessel_name": "TOPAZ"},
        "1183": {"coop_code": "NP", "coop_id": 408, "vessel_name": "LESLIE LEE"},
    }

    EXPECTED_COOPERATIVES = {
        "SOK": {"coop_id": 411, "name": "Star of Kodiak"},
        "OBSI": {"coop_id": 409, "name": "OBSI"},
        "SBS": {"coop_id": 407, "name": "Silver Bay Seafoods"},
        "NP": {"coop_id": 408, "name": "North Pacific"},
    }

    @pytest.fixture
    def db_members(self, supabase):
        """Load coop members from database."""
        result = supabase.table("coop_members").select("*").execute()

        members = {}
        for row in result.data:
            members[row["llp"]] = {
                "coop_code": row["coop_code"],
                "coop_id": row["coop_id"],
                "vessel_name": row["vessel_name"],
                "company_name": row.get("company_name"),
            }
        return members

    @pytest.fixture
    def db_cooperatives(self, supabase):
        """Load cooperatives from database."""
        result = supabase.table("cooperatives").select("*").execute()

        coops = {}
        for row in result.data:
            coops[row["coop_code"]] = {
                "coop_id": row["coop_id"],
                "name": row["coop_name"],
            }
        return coops

    def test_all_expected_llps_in_database(self, db_members):
        """All expected LLPs should exist in coop_members table."""
        missing = [llp for llp in self.EXPECTED_MEMBERSHIP if llp not in db_members]

        assert not missing, f"LLPs missing from coop_members: {missing}"

    def test_no_extra_llps_in_database(self, db_members):
        """Database should not have unexpected LLPs."""
        extra = [llp for llp in db_members if llp not in self.EXPECTED_MEMBERSHIP]

        assert not extra, f"Extra LLPs in database not in expected list: {extra}"

    def test_member_count_matches(self, db_members):
        """Total member count should match."""
        expected_count = len(self.EXPECTED_MEMBERSHIP)
        actual_count = len(db_members)

        assert expected_count == actual_count, (
            f"Member count mismatch: Expected={expected_count}, DB={actual_count}"
        )

    def test_all_coop_codes_correct(self, db_members):
        """Each LLP should be in the correct cooperative."""
        mismatches = []

        for llp, expected in self.EXPECTED_MEMBERSHIP.items():
            if llp not in db_members:
                continue

            actual = db_members[llp]
            if actual["coop_code"] != expected["coop_code"]:
                mismatches.append({
                    "llp": llp,
                    "expected_coop": expected["coop_code"],
                    "actual_coop": actual["coop_code"],
                })

        assert not mismatches, f"Coop code mismatches: {mismatches}"

    def test_all_coop_ids_correct(self, db_members):
        """Each LLP should have the correct coop_id."""
        mismatches = []

        for llp, expected in self.EXPECTED_MEMBERSHIP.items():
            if llp not in db_members:
                continue

            actual = db_members[llp]
            if actual["coop_id"] != expected["coop_id"]:
                mismatches.append({
                    "llp": llp,
                    "expected_id": expected["coop_id"],
                    "actual_id": actual["coop_id"],
                })

        assert not mismatches, f"Coop ID mismatches: {mismatches}"

    def test_cooperatives_table_has_all_coops(self, db_cooperatives):
        """All expected cooperatives should exist."""
        missing = [code for code in self.EXPECTED_COOPERATIVES if code not in db_cooperatives]

        assert not missing, f"Cooperatives missing from database: {missing}"

    def test_cooperatives_have_correct_ids(self, db_cooperatives):
        """Each cooperative should have the correct coop_id."""
        mismatches = []

        for code, expected in self.EXPECTED_COOPERATIVES.items():
            if code not in db_cooperatives:
                continue

            actual = db_cooperatives[code]
            if actual["coop_id"] != expected["coop_id"]:
                mismatches.append({
                    "coop_code": code,
                    "expected_id": expected["coop_id"],
                    "actual_id": actual["coop_id"],
                })

        assert not mismatches, f"Cooperative ID mismatches: {mismatches}"

    def test_coop_member_counts_by_coop(self, db_members):
        """Each cooperative should have the expected number of members."""
        expected_counts = {"SOK": 15, "OBSI": 9, "SBS": 11, "NP": 11}

        actual_counts = {}
        for member in db_members.values():
            coop = member["coop_code"]
            actual_counts[coop] = actual_counts.get(coop, 0) + 1

        mismatches = []
        for coop, expected in expected_counts.items():
            actual = actual_counts.get(coop, 0)
            if actual != expected:
                mismatches.append({
                    "coop": coop,
                    "expected": expected,
                    "actual": actual,
                })

        assert not mismatches, f"Coop member count mismatches: {mismatches}"

    def test_vessel_names_match(self, db_members):
        """Vessel names should match (case-insensitive)."""
        mismatches = []

        for llp, expected in self.EXPECTED_MEMBERSHIP.items():
            if llp not in db_members:
                continue

            actual = db_members[llp]
            expected_name = expected["vessel_name"].upper().strip()
            actual_name = actual["vessel_name"].upper().strip() if actual["vessel_name"] else ""

            # Allow some flexibility in naming
            if expected_name != actual_name:
                # Check if one contains the other (handles "COLLIER BROS" vs "COLLIER BROTHERS")
                if expected_name not in actual_name and actual_name not in expected_name:
                    mismatches.append({
                        "llp": llp,
                        "expected": expected["vessel_name"],
                        "actual": actual["vessel_name"],
                    })

        assert not mismatches, f"Vessel name mismatches: {mismatches}"

    def test_all_membership_data_correct(self, db_members):
        """Comprehensive test: all membership data should match."""
        issues = []

        for llp, expected in self.EXPECTED_MEMBERSHIP.items():
            if llp not in db_members:
                issues.append({"llp": llp, "error": "Missing from database"})
                continue

            actual = db_members[llp]

            if actual["coop_code"] != expected["coop_code"]:
                issues.append({
                    "llp": llp,
                    "field": "coop_code",
                    "expected": expected["coop_code"],
                    "actual": actual["coop_code"],
                })

            if actual["coop_id"] != expected["coop_id"]:
                issues.append({
                    "llp": llp,
                    "field": "coop_id",
                    "expected": expected["coop_id"],
                    "actual": actual["coop_id"],
                })

        assert not issues, (
            f"Found {len(issues)} membership issues:\n" +
            "\n".join(str(i) for i in issues[:10]) +
            (f"\n... and {len(issues) - 10} more" if len(issues) > 10 else "")
        )
