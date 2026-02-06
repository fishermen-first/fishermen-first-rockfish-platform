---
name: streamlit-ui-patterns
description: UI patterns and styling conventions for the Fishermen First Streamlit application. Use this when building new pages, components, or modifying existing UI.
---

# Streamlit UI Patterns - Fishermen First

## Brand Colors

```python
from app.utils.styles import NAVY, GRAY_TEXT, GRAY_BG, WHITE

NAVY = "#1e3a5f"       # Primary brand color (sidebar, headers, buttons)
GRAY_TEXT = "#64748b"  # Secondary text, labels
GRAY_BG = "#f8fafc"    # Page background
WHITE = "#ffffff"      # Cards, containers
```

## Page Structure

Every page follows this structure:

```python
from app.utils.styles import page_header, section_header, apply_page_styling

def show():
    """Entry point - called by main.py router."""
    # 1. Page header (title + subtitle)
    page_header("Page Title", "Optional subtitle with context")

    # 2. Sections with headers
    section_header("SECTION NAME", "📊")  # Icon optional

    # Content here...

    section_header("ANOTHER SECTION", "📋")

    # More content...
```

**Note:** `apply_page_styling()` is called once in `main.py` - don't call it in individual views.

## Headers

### Page Header
```python
page_header("Dashboard", "Season 2026 • Last updated: January 28, 2026")
```
- Large title (2rem)
- Gray subtitle with context
- Use for page identification

### Section Header
```python
section_header("VESSELS NEEDING ATTENTION", "⚠️")
section_header("QUOTA REMAINING BY VESSEL", "📋")
section_header("SPECIES", "🐟")
```
- UPPERCASE text
- Gray color, 1.1rem
- Optional emoji icon prefix
- Creates visual separation between sections

## Data Display

### Tables with st.dataframe
```python
column_config = {
    "vessel_name": st.column_config.TextColumn("Vessel"),
    "llp": st.column_config.TextColumn("LLP"),
    "remaining_lbs": st.column_config.NumberColumn("Remaining (lbs)", format="%,.0f"),
    "pct_remaining": st.column_config.ProgressColumn("% Remaining", min_value=0, max_value=100, format="%.1f%%"),
}

st.dataframe(
    df,
    column_config=column_config,
    use_container_width=True,
    hide_index=True,
    height=500  # Fixed height for scrolling
)

st.caption(f"Showing {len(df)} vessels")  # Row count below table
```

### Metrics (KPIs)
```python
# Simple metric with border
st.metric("Vessels", total_vessels, border=True)

# Metric with delta (color indicates status)
st.metric(
    "At Risk",
    int(vessels_at_risk),
    delta="critical" if vessels_at_risk > 0 else None,
    delta_color="inverse" if vessels_at_risk > 0 else "off",
    border=True
)

# Horizontal layout for metric row
with st.container(horizontal=True):
    st.metric("Metric 1", value1, border=True)
    st.metric("Metric 2", value2, border=True)
    st.metric("Metric 3", value3, border=True)
```

### Risk Level Colors
```python
from app.utils.formatting import get_risk_level, get_pct_color, RISK_COLORS

# RISK_COLORS = {
#     "critical": "#dc2626",  # red - <10%
#     "warning": "#d97706",   # amber - <50%
#     "ok": "#059669",        # green - >=50%
#     "na": "#94a3b8",        # gray - N/A
# }

risk = get_risk_level(pct)  # Returns: "critical", "warning", "ok", or "na"
color = get_pct_color(pct)   # Returns hex color based on risk
```

### Status Indicators
```python
# Emoji dots for status
if pct < 10:
    color = "🔴"  # Critical
elif pct < 50:
    color = "🟡"  # Warning
else:
    color = "🟢"  # OK

# Status emoji mapping
status_emoji = {
    "pending": "⏳",
    "shared": "✅",
    "dismissed": "❌",
    "resolved": "🔵"
}.get(status, "❓")
```

## Forms

### Basic Form Pattern
```python
section_header("FORM SECTION", "📝")

with st.form("form_name", clear_on_submit=False):
    # Form fields
    field1 = st.text_input("Label", placeholder="Hint text")
    field2 = st.selectbox("Options", options=["A", "B", "C"])
    field3 = st.text_area("Details", max_chars=1000, placeholder="Description...")

    # Submit button - always at end, full width, primary type
    submitted = st.form_submit_button("Submit", use_container_width=True, type="primary")

if submitted:
    # Validation
    if not field1:
        st.error("Field 1 is required.")
    else:
        # Process submission
        success, error = save_data(...)
        if success:
            st.success("Saved successfully!")
            st.rerun()  # Refresh to show new data
        else:
            st.error(f"Failed: {error}")
```

### Form Outside st.form (Dynamic Fields)
When you need dynamic fields (add/remove items), put controls outside the form:

```python
section_header("DYNAMIC SECTION", "📍")
st.caption("Explanatory text here")

# Dynamic content OUTSIDE form
items = render_dynamic_items(key_prefix="my_form")

section_header("SUBMIT", "📝")

with st.form("submit_form"):
    optional_field = st.text_area("Notes", placeholder="Optional...")
    submitted = st.form_submit_button("Submit", use_container_width=True, type="primary")

if submitted:
    # Use `items` from above
    process(items, optional_field)
```

## Layout

### Two-Column Layout
```python
col1, col2 = st.columns(2)

with col1:
    st.text_input("Left Field")

with col2:
    st.text_input("Right Field")
```

### Three-Column with Proportions
```python
col1, col2, col3 = st.columns([2, 2, 1])  # Proportional widths
```

### Bordered Container
```python
with st.container(border=True):
    if data.empty:
        st.success("No issues found")
    else:
        for item in data:
            st.markdown(f"**{item.name}** - {item.status}")
```

### Horizontal Container (Responsive)
```python
with st.container(horizontal=True):
    # Items wrap on small screens
    st.metric("A", 1, border=True)
    st.metric("B", 2, border=True)
    st.metric("C", 3, border=True)
```

## Messages

```python
st.success("Operation completed successfully!")
st.error("Something went wrong: {error}")
st.warning("No data found for the selected filters.")
st.info("Your request is being processed.")
st.caption("Showing 25 of 100 items")  # Subtle footer text
```

## Caching

```python
@st.cache_data(ttl=60)  # Cache for 60 seconds (frequently changing data)
def _fetch_live_data():
    response = supabase.table("table").select("*").execute()
    return response.data

@st.cache_data(ttl=300)  # Cache for 5 minutes (reference data)
def _fetch_reference_data():
    response = supabase.table("species").select("*").execute()
    return response.data
```

**Pattern:** Prefix cached functions with `_` to indicate they're internal.

## Reusable Components

Create components in `app/components/` for reusable UI:

```python
# app/components/my_component.py
import streamlit as st

def render_my_component(key_prefix: str, **kwargs) -> dict:
    """
    Render a reusable component.

    Args:
        key_prefix: Unique prefix for widget keys (required for multiple instances)
        **kwargs: Additional configuration

    Returns:
        Dict with collected values
    """
    col1, col2 = st.columns(2)

    with col1:
        value1 = st.text_input("Field 1", key=f"{key_prefix}_field1")

    with col2:
        value2 = st.number_input("Field 2", key=f"{key_prefix}_field2")

    return {"field1": value1, "field2": value2}
```

**Key patterns:**
- Always accept `key_prefix` for widget keys
- Return collected data as dict
- Document with docstrings

## Navigation Icons

Standard icons used in sidebar navigation:
```python
icons = {
    "dashboard": "📊",
    "alerts": "⚠️",
    "account": "💰",
    "transfers": "🔄",
    "allocations": "📈",
    "rosters": "👥",
    "upload": "📤",
    "vessel": "🚢",
    "report": "📍",
    "processor": "🏭",
    "list": "📋",
    "species": "🐟",
    "location": "📍",
    "notes": "📝",
    "history": "📜",
    "compass": "🧭",
}
```

## Common Patterns

### Role-Based Access
```python
def show():
    role = st.session_state.get("user_role")
    if role not in ["admin", "manager"]:
        st.error("You don't have permission to access this page.")
        return

    # Rest of page...
```

### Loading User Context
```python
user_llp = st.session_state.get("user_llp")
org_id = st.session_state.get("org_id")
user_id = st.session_state.user.id if st.session_state.user else None
```

### Empty State Handling
```python
if df.empty:
    st.warning("No data found for the selected criteria.")
    return

# Continue with data display...
```

### Dividers Between Sections
```python
section_header("SECTION 1", "📊")
# content...

st.divider()  # Visual separator

section_header("SECTION 2", "📋")
# content...
```
