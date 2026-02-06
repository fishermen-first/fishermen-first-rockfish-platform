"""
Generate high-quality marketing screenshots with anonymized demo data.

This script creates standalone Streamlit pages with realistic but fake data,
suitable for marketing materials.

Usage:
    streamlit run scripts/generate_marketing_screenshots.py

The screenshots can be captured using browser screenshot tools or
Streamlit's built-in screenshot feature.
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import random

# ============================================================================
# BRAND CONSTANTS (matching app/utils/styles.py)
# ============================================================================
NAVY = "#1e3a5f"
GRAY_TEXT = "#64748b"
GRAY_BG = "#f8fafc"
WHITE = "#ffffff"

# ============================================================================
# ANONYMIZED DEMO DATA
# ============================================================================

# Fictional demo vessel names (clearly not real)
DEMO_VESSELS = [
    {"llp": "LLP-50001", "vessel_name": "F/V Demo Star", "coop_code": "Sample Cooperative A"},
    {"llp": "LLP-50002", "vessel_name": "F/V Example Spirit", "coop_code": "Sample Cooperative A"},
    {"llp": "LLP-50003", "vessel_name": "F/V Test Voyager", "coop_code": "Demo Fisheries Co-op"},
    {"llp": "LLP-50004", "vessel_name": "F/V Sample Harbor", "coop_code": "Demo Fisheries Co-op"},
    {"llp": "LLP-50005", "vessel_name": "F/V Mock Pride", "coop_code": "Example Harvesters"},
    {"llp": "LLP-50006", "vessel_name": "F/V Placeholder Bay", "coop_code": "Example Harvesters"},
    {"llp": "LLP-50007", "vessel_name": "F/V Fictional River", "coop_code": "Test Fleet Cooperative"},
    {"llp": "LLP-50008", "vessel_name": "F/V Demo Sound", "coop_code": "Test Fleet Cooperative"},
    {"llp": "LLP-50009", "vessel_name": "F/V Sample Point", "coop_code": "Sample Cooperative A"},
    {"llp": "LLP-50010", "vessel_name": "F/V Test Fjord", "coop_code": "Demo Fisheries Co-op"},
    {"llp": "LLP-50011", "vessel_name": "F/V Example Explorer", "coop_code": "Example Harvesters"},
    {"llp": "LLP-50012", "vessel_name": "F/V Mock Seas", "coop_code": "Test Fleet Cooperative"},
]

# Species data
SPECIES = {
    "POP": {"full_name": "Pacific Ocean Perch", "code": 141},
    "NR": {"full_name": "Northern Rockfish", "code": 136},
    "Dusky": {"full_name": "Dusky Rockfish", "code": 172},
}

PSC_SPECIES = [
    {"name": "Chinook Salmon", "code": 410},
    {"name": "Non-Chinook Salmon", "code": 420},
    {"name": "Pacific Halibut", "code": 200},
]

# Generate quota data with realistic values
def generate_quota_data():
    """Generate realistic quota remaining data for demo."""
    data = []
    random.seed(42)  # Consistent data for screenshots

    for vessel in DEMO_VESSELS:
        # Base allocations (realistic GOA rockfish amounts)
        pop_alloc = random.randint(80000, 180000)
        nr_alloc = random.randint(40000, 100000)
        dusky_alloc = random.randint(30000, 80000)

        # Simulate harvest progress (some vessels more active)
        harvest_pct = random.uniform(0.3, 0.95)

        # Add some vessels at risk for visual interest
        if vessel["llp"] in ["LLP-50003", "LLP-50008"]:
            harvest_pct = random.uniform(0.92, 0.98)  # Critical
        elif vessel["llp"] in ["LLP-50005", "LLP-50010"]:
            harvest_pct = random.uniform(0.55, 0.70)  # Warning

        data.append({
            "llp": vessel["llp"],
            "vessel_name": vessel["vessel_name"],
            "coop_code": vessel["coop_code"],
            "POP_allocation_lbs": pop_alloc,
            "POP_remaining_lbs": int(pop_alloc * (1 - harvest_pct * random.uniform(0.8, 1.0))),
            "NR_allocation_lbs": nr_alloc,
            "NR_remaining_lbs": int(nr_alloc * (1 - harvest_pct * random.uniform(0.7, 1.0))),
            "Dusky_allocation_lbs": dusky_alloc,
            "Dusky_remaining_lbs": int(dusky_alloc * (1 - harvest_pct * random.uniform(0.6, 1.0))),
        })

    df = pd.DataFrame(data)

    # Calculate percentages
    for species in ["POP", "NR", "Dusky"]:
        df[f"{species}_pct_remaining"] = (
            df[f"{species}_remaining_lbs"] / df[f"{species}_allocation_lbs"] * 100
        )

    return df

def generate_transfer_history():
    """Generate realistic transfer history for demo."""
    random.seed(43)
    transfers = []

    transfer_pairs = [
        ("LLP-50001", "LLP-50003", "POP", 15000, "Pre-season arrangement"),
        ("LLP-50004", "LLP-50002", "NR", 8500, "Quota balancing"),
        ("LLP-50006", "LLP-50008", "Dusky", 12000, "Mid-season transfer"),
        ("LLP-50007", "LLP-50001", "POP", 22000, ""),
        ("LLP-50009", "LLP-50005", "NR", 6750, "Emergency transfer"),
        ("LLP-50002", "LLP-50010", "Dusky", 9200, ""),
        ("LLP-50011", "LLP-50004", "POP", 18500, "Quota reallocation"),
    ]

    for i, (from_llp, to_llp, species, pounds, notes) in enumerate(transfer_pairs):
        from_vessel = next((v["vessel_name"] for v in DEMO_VESSELS if v["llp"] == from_llp), "")
        to_vessel = next((v["vessel_name"] for v in DEMO_VESSELS if v["llp"] == to_llp), "")

        transfers.append({
            "transfer_date": date.today() - timedelta(days=random.randint(1, 45)),
            "from_llp": from_llp,
            "from_vessel": from_vessel,
            "to_llp": to_llp,
            "to_vessel": to_vessel,
            "species": species,
            "pounds": pounds,
            "mt": pounds / 2204.62,
            "notes": notes,
        })

    return pd.DataFrame(transfers).sort_values("transfer_date", ascending=False)

def generate_bycatch_alerts():
    """Generate realistic bycatch alert data for demo."""
    random.seed(44)
    alerts = []

    alert_data = [
        {"species": "Chinook Salmon", "amount": 847, "lat": 57.4521, "lon": -152.8934,
         "vessel": "F/V Demo Star", "status": "pending", "days_ago": 0},
        {"species": "Pacific Halibut", "amount": 2340, "lat": 58.1245, "lon": -151.2367,
         "vessel": "F/V Example Spirit", "status": "shared", "days_ago": 1},
        {"species": "Non-Chinook Salmon", "amount": 1205, "lat": 56.8976, "lon": -153.4521,
         "vessel": "F/V Test Voyager", "status": "pending", "days_ago": 0},
        {"species": "Chinook Salmon", "amount": 523, "lat": 57.9834, "lon": -152.1298,
         "vessel": "F/V Sample Harbor", "status": "resolved", "days_ago": 3},
    ]

    for alert in alert_data:
        alerts.append({
            "species": alert["species"],
            "amount": alert["amount"],
            "location": f"{alert['lat']:.4f}N, {abs(alert['lon']):.4f}W",
            "vessel": alert["vessel"],
            "status": alert["status"],
            "reported": (datetime.now() - timedelta(days=alert["days_ago"])).strftime("%b %d, %Y %H:%M"),
        })

    return alerts


# ============================================================================
# STYLING
# ============================================================================

def apply_marketing_styles():
    """Apply polished styles for marketing screenshots."""
    st.markdown(f"""
    <style>
        /* Clean background */
        .stApp {{
            background-color: {GRAY_BG};
        }}

        .stMainBlockContainer {{
            background-color: {GRAY_BG};
            padding-top: 2rem;
        }}

        /* Styled headers */
        h1 {{
            color: {NAVY} !important;
            font-weight: 700 !important;
        }}

        /* Metric cards */
        [data-testid="stMetric"] {{
            background-color: {WHITE};
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}

        [data-testid="stMetric"] label {{
            color: {GRAY_TEXT} !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }}

        [data-testid="stMetricValue"] {{
            font-size: 2.5rem !important;
            font-weight: 700 !important;
        }}

        /* Table styling */
        .stDataFrame {{
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}

        /* Hide truncation indicators (red corners) in dataframes */
        .stDataFrame [data-testid="StyledFullScreenButton"] {{
            display: none;
        }}

        /* Hide cell overflow indicators */
        .stDataFrame div[data-testid="StyledDataFrameOverflowGradient"],
        .stDataFrame .dvn-cell-overflow-indicator,
        .stDataFrame svg.overflow-icon {{
            display: none !important;
            visibility: hidden !important;
        }}

        /* Ensure text doesn't show overflow */
        .stDataFrame td, .stDataFrame th {{
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }}

        /* Hide Streamlit branding for clean screenshots */
        #MainMenu, footer, header {{
            visibility: hidden;
        }}

        /* Section headers */
        .section-header {{
            color: {GRAY_TEXT};
            font-size: 0.9rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 2rem 0 1rem 0;
        }}

        /* Alert cards */
        .alert-card {{
            background: {WHITE};
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}

        .alert-card.pending {{
            border-left: 4px solid #f59e0b;
        }}

        .alert-card.shared {{
            border-left: 4px solid #10b981;
        }}

        /* Transfer form */
        .transfer-form {{
            background: {WHITE};
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #e2e8f0;
        }}
    </style>
    """, unsafe_allow_html=True)


def format_lbs_short(value: float) -> str:
    """Format pounds as short string (e.g., 15K, 1.2M)."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.0f}K"
    else:
        return f"{value:.0f}"


def page_header(title: str, subtitle: str = None):
    """Render marketing-quality page header."""
    st.markdown(f"""
    <div style="margin-bottom: 1.5rem;">
        <h1 style="margin: 0; font-size: 2.25rem; color: {NAVY};">{title}</h1>
        {f'<p style="color: {GRAY_TEXT}; margin: 0.5rem 0 0 0; font-size: 1.1rem;">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def section_header(text: str, icon: str = ""):
    """Render section header."""
    st.markdown(f"""
    <p class="section-header">{icon} {text}</p>
    """, unsafe_allow_html=True)


def format_lbs(value: float) -> str:
    """Format pounds with commas."""
    return f"{value:,.0f}"


# ============================================================================
# PAGE RENDERERS
# ============================================================================

def render_dashboard():
    """Render the Dashboard page for screenshots."""
    page_header("Dashboard", "Season 2026 | Central GOA Rockfish Program")

    df = generate_quota_data()

    # Calculate totals
    total_vessels = len(df)
    # Use same threshold (15%) as "Vessels Needing Attention" section
    vessels_at_risk = len(df[
        (df["POP_pct_remaining"] < 15) |
        (df["NR_pct_remaining"] < 15) |
        (df["Dusky_pct_remaining"] < 15)
    ])

    total_pop_remaining = df["POP_remaining_lbs"].sum()
    total_pop_allocated = df["POP_allocation_lbs"].sum()
    total_pop_pct = total_pop_remaining / total_pop_allocated * 100

    total_nr_remaining = df["NR_remaining_lbs"].sum()
    total_nr_allocated = df["NR_allocation_lbs"].sum()
    total_nr_pct = total_nr_remaining / total_nr_allocated * 100

    total_dusky_remaining = df["Dusky_remaining_lbs"].sum()
    total_dusky_allocated = df["Dusky_allocation_lbs"].sum()
    total_dusky_pct = total_dusky_remaining / total_dusky_allocated * 100

    # KPI Row
    section_header("FLEET OVERVIEW", "")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        # Count unique co-ops for informative delta
        num_coops = df["coop_code"].nunique()
        st.metric("Active Vessels", total_vessels, delta=f"{num_coops} co-ops", delta_color="off", border=True)

    with col2:
        st.metric(
            "At Risk",
            vessels_at_risk,
            delta="critical" if vessels_at_risk > 0 else None,
            delta_color="inverse",
            border=True
        )

    with col3:
        st.metric(
            "POP Remaining",
            f"{total_pop_pct:.0f}%",
            delta=f"{format_lbs(total_pop_remaining)} lbs",
            delta_color="normal" if total_pop_pct > 50 else "off",
            border=True
        )

    with col4:
        st.metric(
            "NR Remaining",
            f"{total_nr_pct:.0f}%",
            delta=f"{format_lbs(total_nr_remaining)} lbs",
            delta_color="normal" if total_nr_pct > 50 else "off",
            border=True
        )

    with col5:
        st.metric(
            "Dusky Remaining",
            f"{total_dusky_pct:.0f}%",
            delta=f"{format_lbs(total_dusky_remaining)} lbs",
            delta_color="normal" if total_dusky_pct > 50 else "off",
            border=True
        )

    # Vessels needing attention
    section_header("VESSELS NEEDING ATTENTION", "")

    at_risk_df = df[
        (df["POP_pct_remaining"] < 15) |
        (df["NR_pct_remaining"] < 15) |
        (df["Dusky_pct_remaining"] < 15)
    ].head(5)

    with st.container(border=True):
        if at_risk_df.empty:
            st.success("No vessels currently at critical risk levels")
        else:
            for _, row in at_risk_df.iterrows():
                dots = []
                for species in ["POP", "NR", "Dusky"]:
                    pct = row[f"{species}_pct_remaining"]
                    if pct < 10:
                        color = ""
                    elif pct < 50:
                        color = ""
                    else:
                        color = ""
                    dots.append(f"{color} {species}: {pct:.1f}%")

                st.markdown(f"**{row['vessel_name']}** ({row['llp']})  {'  '.join(dots)}")

    # Main quota table
    section_header("QUOTA REMAINING BY VESSEL", "")

    display_df = df[["coop_code", "vessel_name", "llp",
                     "POP_remaining_lbs", "POP_pct_remaining",
                     "NR_remaining_lbs", "NR_pct_remaining",
                     "Dusky_remaining_lbs", "Dusky_pct_remaining"]].copy()

    # Sort by lowest remaining
    display_df["_min_pct"] = display_df[["POP_pct_remaining", "NR_pct_remaining", "Dusky_pct_remaining"]].min(axis=1)
    display_df = display_df.sort_values("_min_pct").drop(columns=["_min_pct"])

    # Format lbs columns as short strings (e.g., "15K")
    display_df["POP_remaining_lbs"] = display_df["POP_remaining_lbs"].apply(format_lbs_short)
    display_df["NR_remaining_lbs"] = display_df["NR_remaining_lbs"].apply(format_lbs_short)
    display_df["Dusky_remaining_lbs"] = display_df["Dusky_remaining_lbs"].apply(format_lbs_short)

    st.dataframe(
        display_df,
        column_config={
            "coop_code": st.column_config.TextColumn("Co-Op", width=150),
            "vessel_name": st.column_config.TextColumn("Vessel", width=140),
            "llp": st.column_config.TextColumn("LLP", width=90),
            "POP_remaining_lbs": st.column_config.TextColumn("POP (lbs)", width=75),
            "POP_pct_remaining": st.column_config.ProgressColumn("POP %", min_value=0, max_value=100, format="%.1f%%", width=90),
            "NR_remaining_lbs": st.column_config.TextColumn("NR (lbs)", width=75),
            "NR_pct_remaining": st.column_config.ProgressColumn("NR %", min_value=0, max_value=100, format="%.1f%%", width=90),
            "Dusky_remaining_lbs": st.column_config.TextColumn("Dusky (lbs)", width=75),
            "Dusky_pct_remaining": st.column_config.ProgressColumn("Dusky %", min_value=0, max_value=100, format="%.1f%%", width=90),
        },
        use_container_width=True,
        hide_index=True,
        height=450
    )

    st.caption(f"Showing {len(display_df)} vessels | Last updated: {datetime.now().strftime('%B %d, %Y')}")


def render_allocations():
    """Render the Allocations page for screenshots."""
    page_header("Allocations", "TAC and vessel quota allocations for Season 2026")

    tab1, tab2, tab3 = st.tabs(["Total Allocation", "Vessel Allocations", "PSC Allocations"])

    with tab1:
        st.subheader("2026 TAC")

        tac_data = [
            {"Species": "Pacific Ocean Perch", "TAC (mt)": 31245, "QS Pool": 28120, "TAC (lbs)": 68_873_000},
            {"Species": "Northern Rockfish", "TAC (mt)": 5890, "QS Pool": 5301, "TAC (lbs)": 12_985_000},
            {"Species": "Dusky Rockfish", "TAC (mt)": 4125, "QS Pool": 3712, "TAC (lbs)": 9_093_000},
            {"Species": "Pacific Cod", "TAC (mt)": None, "QS Pool": None, "TAC (lbs)": 2_450_000},
            {"Species": "Thornyhead", "TAC (mt)": None, "QS Pool": None, "TAC (lbs)": 890_000},
            {"Species": "Sablefish", "TAC (mt)": None, "QS Pool": None, "TAC (lbs)": 1_125_000},
        ]

        tac_df = pd.DataFrame(tac_data)
        st.dataframe(
            tac_df.style.format({
                "TAC (mt)": "{:,.0f}",
                "QS Pool": "{:,.0f}",
                "TAC (lbs)": "{:,.0f}"
            }, na_rep="-"),
            use_container_width=True,
            hide_index=True
        )

    with tab2:
        st.subheader("Starting Quota by Vessel")

        df = generate_quota_data()
        alloc_df = df[["coop_code", "llp", "vessel_name",
                       "POP_allocation_lbs", "NR_allocation_lbs", "Dusky_allocation_lbs"]].copy()
        alloc_df["Total"] = alloc_df["POP_allocation_lbs"] + alloc_df["NR_allocation_lbs"] + alloc_df["Dusky_allocation_lbs"]
        alloc_df = alloc_df.rename(columns={
            "coop_code": "Co-Op",
            "llp": "LLP",
            "vessel_name": "Vessel",
            "POP_allocation_lbs": "POP",
            "NR_allocation_lbs": "NR",
            "Dusky_allocation_lbs": "Dusky"
        })

        st.dataframe(
            alloc_df.style.format({
                "POP": "{:,.0f}",
                "NR": "{:,.0f}",
                "Dusky": "{:,.0f}",
                "Total": "{:,.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )
        st.caption(f"{len(alloc_df)} vessels")

    with tab3:
        st.subheader("PSC Allocations (2026)")

        psc_data = [{"Species": "Halibut", "CV Sector (lbs)": 1_247_000}]
        st.dataframe(
            pd.DataFrame(psc_data).style.format({"CV Sector (lbs)": "{:,.0f}"}),
            use_container_width=True,
            hide_index=True
        )


def render_transfers():
    """Render the Transfers page for screenshots."""
    page_header("Quota Transfers", "Transfer quota between LLPs | Season: 2026")

    # Transfer form section
    section_header("NEW TRANSFER", "")

    with st.container(border=True):
        col1, col2 = st.columns(2)

        vessel_options = [f"{v['llp']} - {v['vessel_name']}" for v in DEMO_VESSELS]

        with col1:
            st.selectbox("From LLP (Source)", options=vessel_options, index=0)

        with col2:
            st.selectbox("To LLP (Destination)", options=vessel_options, index=2)

        col3, col4 = st.columns(2)

        with col3:
            st.selectbox("Species", options=["POP (Pacific Ocean Perch)", "NR (Northern Rockfish)", "Dusky (Dusky Rockfish)"])

        with col4:
            st.number_input("Pounds", min_value=1, value=15000, step=100)
            st.caption("= 6.80 MT")

        # Show available quota
        col_from, col_to = st.columns(2)
        with col_from:
            st.info("**LLP-50001** has **45,230 lbs (20.52 MT)** POP")
        with col_to:
            st.info("**LLP-50003** has **8,450 lbs (3.83 MT)** POP")

        st.text_area("Notes (optional)", placeholder="Enter any notes about this transfer...")
        st.button("Submit Transfer", type="primary", use_container_width=True)

    st.divider()

    # Transfer history
    section_header("TRANSFER HISTORY", "")

    history_df = generate_transfer_history()

    # Format pounds as short strings
    history_df["pounds"] = history_df["pounds"].apply(format_lbs_short)

    st.dataframe(
        history_df,
        column_config={
            "transfer_date": st.column_config.DateColumn("Date", format="YYYY-MM-DD", width=100),
            "from_llp": st.column_config.TextColumn("From LLP", width=90),
            "from_vessel": st.column_config.TextColumn("From Vessel", width=140),
            "to_llp": st.column_config.TextColumn("To LLP", width=90),
            "to_vessel": st.column_config.TextColumn("To Vessel", width=140),
            "species": st.column_config.TextColumn("Species", width=70),
            "pounds": st.column_config.TextColumn("Pounds", width=70),
            "mt": st.column_config.NumberColumn("MT", format="%.2f", width=60),
            "notes": st.column_config.TextColumn("Notes", width=150),
        },
        use_container_width=True,
        hide_index=True
    )
    st.caption(f"{len(history_df)} transfers")


def generate_vessel_owner_data():
    """Generate realistic data for a single vessel owner view."""
    random.seed(45)

    # Pick a specific vessel for the demo
    vessel = DEMO_VESSELS[0]  # F/V Demo Star

    # Quota data with good visual variety
    quota = {
        "POP": {"allocation": 145000, "remaining": 52200, "pct": 36.0},
        "NR": {"allocation": 78000, "remaining": 45500, "pct": 58.3},
        "Dusky": {"allocation": 52000, "remaining": 8400, "pct": 16.2},  # At risk
    }

    # Transfer history for this vessel
    transfers = [
        {"date": date.today() - timedelta(days=5), "direction": "OUT", "species": "POP",
         "pounds": 15000, "other_vessel": "F/V Test Voyager", "other_llp": "LLP-50003",
         "notes": "Pre-season arrangement"},
        {"date": date.today() - timedelta(days=18), "direction": "IN", "species": "NR",
         "pounds": 8500, "other_vessel": "F/V Fictional River", "other_llp": "LLP-50007",
         "notes": ""},
        {"date": date.today() - timedelta(days=32), "direction": "IN", "species": "POP",
         "pounds": 22000, "other_vessel": "F/V Fictional River", "other_llp": "LLP-50007",
         "notes": ""},
        {"date": date.today() - timedelta(days=41), "direction": "OUT", "species": "Dusky",
         "pounds": 6500, "other_vessel": "F/V Example Spirit", "other_llp": "LLP-50002",
         "notes": "Quota balancing"},
    ]

    # Harvest records
    harvests = [
        {"date": date.today() - timedelta(days=2), "species": "POP", "pounds": 18500, "processor": "Demo Processing Inc."},
        {"date": date.today() - timedelta(days=8), "species": "NR", "pounds": 12300, "processor": "Demo Processing Inc."},
        {"date": date.today() - timedelta(days=12), "species": "POP", "pounds": 24100, "processor": "Sample Seafoods LLC"},
        {"date": date.today() - timedelta(days=15), "species": "Dusky", "pounds": 9800, "processor": "Demo Processing Inc."},
        {"date": date.today() - timedelta(days=22), "species": "POP", "pounds": 31200, "processor": "Sample Seafoods LLC"},
        {"date": date.today() - timedelta(days=28), "species": "NR", "pounds": 8700, "processor": "Demo Processing Inc."},
        {"date": date.today() - timedelta(days=35), "species": "Dusky", "pounds": 15400, "processor": "Sample Seafoods LLC"},
    ]

    return vessel, quota, transfers, harvests


def render_vessel_owner():
    """Render the Vessel Owner View page for screenshots."""
    vessel, quota, transfers, harvests = generate_vessel_owner_data()

    page_header(f"My Vessel: {vessel['vessel_name']}", f"LLP: {vessel['llp']} | Co-Op: {vessel['coop_code']} | Season: 2026")

    # --- QUOTA REMAINING ---
    section_header("QUOTA REMAINING", "")

    col1, col2, col3 = st.columns(3)

    for i, (species, col) in enumerate(zip(["POP", "NR", "Dusky"], [col1, col2, col3])):
        data = quota[species]
        pct = data["pct"]

        # Color based on risk level
        if pct < 20:
            color = "#dc2626"  # Red - critical
            status = "⚠️ Critical"
        elif pct < 50:
            color = "#f59e0b"  # Amber - warning
            status = "⚡ Low"
        else:
            color = "#059669"  # Green - healthy
            status = "✓ Healthy"

        with col:
            st.markdown(f"""
            <div style="background-color: {WHITE}; border: 1px solid #e2e8f0; border-radius: 12px;
                        padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center;
                        border-left: 4px solid {color};">
                <div style="color: {GRAY_TEXT}; font-size: 14px; font-weight: 600;
                            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
                    {species}
                </div>
                <div style="font-size: 32px; font-weight: 700; color: {NAVY};">
                    {data['remaining']:,}
                </div>
                <div style="color: {GRAY_TEXT}; font-size: 13px; margin-top: 4px;">lbs remaining</div>
                <div style="margin-top: 12px; padding: 6px 12px; background: {color}15;
                            border-radius: 20px; display: inline-block;">
                    <span style="color: {color}; font-weight: 600; font-size: 15px;">{pct:.0f}%</span>
                    <span style="color: {GRAY_TEXT}; font-size: 12px; margin-left: 4px;">{status}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- TRANSFER HISTORY ---
    section_header("TRANSFER HISTORY", "")

    transfer_rows = []
    for t in transfers:
        direction_badge = (
            '<span style="background: #dcfce7; color: #059669; padding: 2px 8px; border-radius: 4px; font-weight: 600;">IN</span>'
            if t["direction"] == "IN" else
            '<span style="background: #fee2e2; color: #dc2626; padding: 2px 8px; border-radius: 4px; font-weight: 600;">OUT</span>'
        )
        transfer_rows.append({
            "Date": t["date"],
            "Direction": t["direction"],
            "Species": t["species"],
            "Pounds": format_lbs_short(t["pounds"]),
            "Other Vessel": f"{t['other_vessel']} ({t['other_llp']})",
            "Notes": t["notes"]
        })

    df = pd.DataFrame(transfer_rows)

    st.dataframe(
        df,
        column_config={
            "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD", width=110),
            "Direction": st.column_config.TextColumn("Direction", width=90),
            "Species": st.column_config.TextColumn("Species", width=80),
            "Pounds": st.column_config.TextColumn("Pounds", width=80),
            "Other Vessel": st.column_config.TextColumn("Other Vessel", width=250),
            "Notes": st.column_config.TextColumn("Notes", width=180),
        },
        use_container_width=True,
        hide_index=True
    )
    st.caption(f"{len(transfers)} transfers this season")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- HARVEST RECORDS ---
    section_header("HARVEST RECORDS", "")

    harvest_df = pd.DataFrame(harvests)
    harvest_df = harvest_df.rename(columns={
        "date": "Date", "species": "Species", "pounds": "Pounds", "processor": "Processor"
    })

    # Format pounds as short strings
    harvest_df["Pounds"] = harvest_df["Pounds"].apply(format_lbs_short)

    st.dataframe(
        harvest_df,
        column_config={
            "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD", width=110),
            "Species": st.column_config.TextColumn("Species", width=100),
            "Pounds": st.column_config.TextColumn("Pounds", width=80),
            "Processor": st.column_config.TextColumn("Processor", width=200),
        },
        use_container_width=True,
        hide_index=True
    )
    st.caption(f"{len(harvests)} harvest records this season")


def render_bycatch_alerts():
    """Render the Bycatch Alerts page for screenshots."""
    page_header("Bycatch Alerts", "Review and share bycatch hotspot reports with the fleet")

    # Create alert section
    with st.expander("CREATE NEW ALERT", expanded=False, icon=":material/pin_drop:"):
        st.caption("Report a bycatch hotspot on behalf of a vessel")
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Reporting Vessel", options=["Select vessel..."], disabled=True)
        with col2:
            st.selectbox("Species", options=["Select species..."], disabled=True)

    # Filters
    section_header("FILTERS", "")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.selectbox("Cooperative", options=["All Co-ops", "Sample Cooperative A", "Demo Fisheries Co-op", "Example Harvesters", "Test Fleet Cooperative"])
    with col2:
        st.selectbox("Species", options=["All Species", "Chinook Salmon", "Non-Chinook Salmon", "Pacific Halibut"], key="filter_species")
    with col3:
        st.date_input("From Date", value=date.today() - timedelta(days=30))
    with col4:
        st.date_input("To Date", value=date.today())

    # View selector
    section_header("ALERTS", "")

    view = st.segmented_control(
        "View",
        options=["Pending", "Shared", "Resolved", "All"],
        default="Pending",
        key="alert_view"
    )

    # Alert cards
    alerts = generate_bycatch_alerts()
    pending_alerts = [a for a in alerts if a["status"] == "pending"]

    st.markdown(f"**{len(pending_alerts)} pending alert(s)**")

    for alert in pending_alerts:
        st.markdown(f"""
        <div class="alert-card pending">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <span style="font-size: 1.2rem; font-weight: 600;">{alert['species']}</span>
                    <span style="margin-left: 1rem; color: {GRAY_TEXT};"> Pending</span>
                </div>
                <div style="color: {GRAY_TEXT}; font-size: 0.9rem;">{alert['reported']}</div>
            </div>
            <div style="margin-top: 0.5rem; color: {GRAY_TEXT};">
                <strong>Vessel:</strong> {alert['vessel']} &nbsp;|&nbsp;
                <strong>Amount:</strong> {alert['amount']:,} &nbsp;|&nbsp;
                <strong>Location:</strong> {alert['location']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        with col1:
            st.button("Edit", key=f"edit_{alert['species']}", use_container_width=True)
        with col2:
            st.button("Preview", key=f"preview_{alert['species']}", use_container_width=True)
        with col3:
            st.button("Share", key=f"share_{alert['species']}", type="primary", use_container_width=True)
        with col4:
            st.button("Dismiss", key=f"dismiss_{alert['species']}", use_container_width=True)

        st.divider()


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.set_page_config(
        page_title="Fishermen First - Demo",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    apply_marketing_styles()

    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 1rem; margin-bottom: 1rem;">
            <h2 style="color: {NAVY}; margin: 0;">Fishermen First</h2>
            <p style="color: {GRAY_TEXT}; margin: 0.5rem 0 0 0; font-size: 0.9rem;">
                Rockfish Platform
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        page = st.radio(
            "Navigation",
            options=["Dashboard", "Allocations", "Transfers", "Vessel Owner", "Bycatch Alerts"],
            label_visibility="collapsed"
        )

        st.divider()

        # Demo mode indicator
        st.info("**Demo Mode**\n\nThis page displays anonymized sample data for marketing screenshots.")

        st.markdown("""
        **Screenshot Tips:**
        1. Use browser zoom (Ctrl/Cmd +/-) to adjust size
        2. Press F11 for fullscreen
        3. Use browser's screenshot tool or Snipping Tool
        """)

    # Render selected page
    if page == "Dashboard":
        render_dashboard()
    elif page == "Allocations":
        render_allocations()
    elif page == "Transfers":
        render_transfers()
    elif page == "Vessel Owner":
        render_vessel_owner()
    elif page == "Bycatch Alerts":
        render_bycatch_alerts()


if __name__ == "__main__":
    main()
