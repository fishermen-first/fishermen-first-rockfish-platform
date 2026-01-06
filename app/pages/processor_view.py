"""Processor view page - for processor role users."""

import streamlit as st


def show():
    """Display the processor view page."""
    st.header("Processor View")

    processor_code = st.session_state.get("processor_code")
    st.write(f"Logged in as processor: {processor_code}")

    st.info("Species processed and limits coming soon")
