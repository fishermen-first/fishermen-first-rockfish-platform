# Example: Minimal Page Template

A minimal starting point for new pages.

```python
"""Page Name - Brief description."""

import streamlit as st
from app.config import supabase
from app.auth import require_role


@st.cache_data(ttl=300)
def _fetch_data():
    """Fetch data from database."""
    response = supabase.table("table_name").select("*").execute()
    return response.data if response.data else []


def show():
    """Display the page."""
    from app.utils.styles import page_header, section_header

    if not require_role("manager"):
        return

    page_header("Page Title", "Page description")

    org_id = st.session_state.get("org_id")
    if not org_id:
        st.error("Organization not set.")
        return

    section_header("CONTENT", "📊")

    data = _fetch_data()
    if data:
        st.dataframe(data)
    else:
        st.info("No data found.")
```

## Key Elements

1. **Docstring** - Brief description at top
2. **Imports** - streamlit, supabase, require_role
3. **Cached fetch** - `@st.cache_data` with TTL
4. **show() function** - Main entry point
5. **Access check** - `require_role()` first
6. **page_header()** - Consistent title styling
7. **org_id check** - Multi-tenant validation
8. **section_header()** - Section styling with icon
