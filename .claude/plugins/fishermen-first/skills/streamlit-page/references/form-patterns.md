# Form Patterns for Fishermen First

Detailed form patterns for data entry, validation, and submission.

## Form Basics

### Standard Form Structure

```python
with st.form("unique_form_key", clear_on_submit=True):
    # Form fields here
    field1 = st.text_input("Label")
    field2 = st.number_input("Number", min_value=0)

    # Submit button (must be inside form)
    submitted = st.form_submit_button(
        "Submit",
        type="primary",
        use_container_width=True
    )

    if submitted:
        # Handle submission
        pass
```

### Form with Icon Button

```python
submitted = st.form_submit_button(
    "Submit Alert",
    type="primary",
    use_container_width=True,
    icon=":material/warning:"
)
```

## Dynamic Forms

### Select Outside Form (Recommended Pattern)

When selection affects other fields or shows computed values:

```python
# SELECT OUTSIDE FORM - triggers immediate UI updates
species = st.selectbox("Species", options, key="species_select")

# Computed display based on selection
if species:
    unit = get_species_unit(species)
    st.info(f"Unit: {unit}")

# FORM for final submission
with st.form("entry_form"):
    amount = st.number_input(f"Amount ({unit})", min_value=0)
    submitted = st.form_submit_button("Submit")

    if submitted:
        process_submission(species, amount, unit)
```

### Multi-Step Forms with Session State

```python
# Step tracking
if "form_step" not in st.session_state:
    st.session_state.form_step = 1

# Step 1: Basic Info
if st.session_state.form_step == 1:
    with st.form("step1"):
        name = st.text_input("Name")
        if st.form_submit_button("Next"):
            st.session_state.form_data = {"name": name}
            st.session_state.form_step = 2
            st.rerun()

# Step 2: Details
elif st.session_state.form_step == 2:
    st.write(f"Name: {st.session_state.form_data['name']}")
    with st.form("step2"):
        details = st.text_area("Details")
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Back"):
                st.session_state.form_step = 1
                st.rerun()
        with col2:
            if st.form_submit_button("Submit", type="primary"):
                final_data = {**st.session_state.form_data, "details": details}
                save_record(final_data)
                st.session_state.form_step = 1
                del st.session_state.form_data
                st.rerun()
```

## Field Types

### Text Fields

```python
# Single line
name = st.text_input("Name", max_chars=100, placeholder="Enter name...")

# Multi-line
details = st.text_area(
    "Details (optional)",
    max_chars=1000,
    placeholder="Enter details...",
    help="Additional information"
)

# Password
password = st.text_input("Password", type="password")
```

### Number Fields

```python
# Integer
count = st.number_input("Count", min_value=1, max_value=1000, value=1, step=1)

# Float
amount = st.number_input(
    "Amount (lbs)",
    min_value=0.0,
    max_value=1000000.0,
    value=100.0,
    step=10.0,
    format="%.2f"
)

# GPS Coordinates
latitude = st.number_input(
    "Latitude",
    min_value=50.0,
    max_value=72.0,
    value=57.0,
    step=0.001,
    format="%.6f",
    help="50.0 to 72.0 for Alaska"
)
```

### Selection Fields

```python
# Single select
option = st.selectbox(
    "Select One",
    options=["Option A", "Option B", "Option C"],
    index=None,  # No default selection
    placeholder="Choose..."
)

# Multi-select
options = st.multiselect(
    "Select Multiple",
    options=["A", "B", "C", "D"],
    default=["A"]
)

# Radio buttons
choice = st.radio(
    "Choose",
    options=["Yes", "No"],
    horizontal=True
)

# Checkbox
agreed = st.checkbox("I agree to the terms")
```

### Date/Time Fields

```python
# Date
selected_date = st.date_input("Date", value=date.today())

# Date range
date_range = st.date_input(
    "Date Range",
    value=(date.today() - timedelta(days=30), date.today())
)

# Time
selected_time = st.time_input("Time", value=time(9, 0))
```

### File Upload

```python
uploaded_file = st.file_uploader(
    "Upload CSV",
    type=["csv"],
    help="Select a CSV file"
)

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.dataframe(df)
```

## Validation Patterns

### Inline Validation

```python
if submitted:
    errors = []

    if not field1:
        errors.append("Field 1 is required.")

    if field2 <= 0:
        errors.append("Field 2 must be positive.")

    if field2 > max_allowed:
        errors.append(f"Field 2 cannot exceed {max_allowed}.")

    if errors:
        for error in errors:
            st.error(error)
    else:
        # Process valid submission
        success, error = save_record(data)
        if success:
            st.success("Saved!")
            st.rerun()
        else:
            st.error(f"Failed: {error}")
```

### Validation Function

```python
def validate_transfer(from_llp, to_llp, amount, available) -> tuple[bool, list[str]]:
    """Validate transfer form input."""
    errors = []

    if from_llp == to_llp:
        errors.append("Cannot transfer to the same vessel.")

    if amount <= 0:
        errors.append("Amount must be greater than zero.")

    if amount > available:
        errors.append(f"Amount exceeds available quota ({available:,.0f} lbs).")

    return len(errors) == 0, errors


# Usage
if submitted:
    valid, errors = validate_transfer(from_llp, to_llp, amount, available)
    if not valid:
        for e in errors:
            st.error(e)
    else:
        # Process
```

### Real-Time Validation Display

```python
# Outside form for immediate feedback
from_llp = st.selectbox("From", options)
to_llp = st.selectbox("To", options)

# Show validation status immediately
if from_llp and to_llp:
    if from_llp == to_llp:
        st.error("Cannot transfer to the same vessel.")
    else:
        available = get_available(from_llp)
        st.success(f"Available: {available:,.0f} lbs")

# Form still validates on submit
with st.form("transfer"):
    amount = st.number_input("Amount")
    submitted = st.form_submit_button("Submit")
```

## Layout Patterns

### Two-Column Form

```python
with st.form("form"):
    col1, col2 = st.columns(2)

    with col1:
        field1 = st.text_input("Field 1")
        field3 = st.number_input("Field 3")

    with col2:
        field2 = st.selectbox("Field 2", options)
        field4 = st.date_input("Field 4")

    # Full width
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Submit", use_container_width=True)
```

### Form with Sidebar

```python
# Filters in sidebar
with st.sidebar:
    filter1 = st.selectbox("Filter 1", options)
    filter2 = st.date_input("Date")

# Form in main area
with st.form("main_form"):
    # Fields filtered by sidebar selection
    filtered_options = get_filtered(filter1, filter2)
    selected = st.selectbox("Select", filtered_options)
    submitted = st.form_submit_button("Submit")
```

### Inline Edit Form

```python
def render_item_with_edit(item, user_id):
    """Render item with inline edit capability."""

    # Display mode
    if not st.session_state.get(f"editing_{item['id']}"):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{item['name']}** - {item['value']}")
        with col2:
            if st.button("Edit", key=f"edit_btn_{item['id']}"):
                st.session_state[f"editing_{item['id']}"] = True
                st.rerun()

    # Edit mode
    else:
        with st.form(f"edit_form_{item['id']}"):
            new_name = st.text_input("Name", value=item["name"])
            new_value = st.number_input("Value", value=item["value"])

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Save", type="primary"):
                    update_item(item["id"], new_name, new_value)
                    st.session_state[f"editing_{item['id']}"] = False
                    st.rerun()
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state[f"editing_{item['id']}"] = False
                    st.rerun()
```

## Submission Patterns

### Basic Submit with Feedback

```python
if submitted:
    with st.spinner("Saving..."):
        success, error = save_record(data)

    if success:
        st.success("Record saved successfully!")
        st.rerun()
    else:
        st.error(f"Failed to save: {error}")
```

### Submit with Confirmation

```python
if submitted:
    st.session_state.confirm_submit = True
    st.session_state.pending_data = data

if st.session_state.get("confirm_submit"):
    st.warning("Are you sure you want to submit?")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Yes, submit"):
            success, error = save_record(st.session_state.pending_data)
            st.session_state.confirm_submit = False
            st.session_state.pending_data = None
            if success:
                st.success("Submitted!")
            st.rerun()

    with col2:
        if st.button("Cancel"):
            st.session_state.confirm_submit = False
            st.session_state.pending_data = None
            st.rerun()
```

### Batch Submit

```python
with st.form("batch_form"):
    st.write("Enter multiple records:")

    records = []
    for i in range(3):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(f"Name {i+1}", key=f"name_{i}")
        with col2:
            value = st.number_input(f"Value {i+1}", key=f"value_{i}")
        if name:  # Only include non-empty
            records.append({"name": name, "value": value})

    if st.form_submit_button("Submit All"):
        if not records:
            st.error("Enter at least one record.")
        else:
            success_count = 0
            for record in records:
                success, _ = save_record(record)
                if success:
                    success_count += 1
            st.success(f"Saved {success_count} of {len(records)} records.")
            st.rerun()
```

## Special Patterns

### Form in Expander

```python
with st.expander("Add New Item", expanded=False):
    with st.form("add_form"):
        name = st.text_input("Name")
        submitted = st.form_submit_button("Add")

        if submitted and name:
            save_item(name)
            st.rerun()
```

### Form in Tab

```python
tab_view, tab_add = st.tabs(["View Items", "Add New"])

with tab_view:
    items = fetch_items()
    for item in items:
        st.write(item["name"])

with tab_add:
    with st.form("add_form"):
        name = st.text_input("Name")
        if st.form_submit_button("Add"):
            save_item(name)
            st.rerun()
```

### Conditional Fields

```python
category = st.selectbox("Category", ["Type A", "Type B"])

with st.form("conditional_form"):
    name = st.text_input("Name")

    # Show different fields based on category
    if category == "Type A":
        field_a = st.number_input("Type A Field")
        data = {"name": name, "field_a": field_a}
    else:
        field_b = st.text_input("Type B Field")
        data = {"name": name, "field_b": field_b}

    if st.form_submit_button("Submit"):
        save_record(category, data)
```
