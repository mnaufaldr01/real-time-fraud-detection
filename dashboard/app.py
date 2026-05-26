"""Streamlit fraud detection dashboard — General + Velocity views powered by dbt marts."""

import streamlit as st

from dashboard import refresh
from dashboard.views import general, velocity

st.set_page_config(page_title="Fraud Detection Dashboard", layout="wide", page_icon="🛡️")

st.title("Real-Time Fraud Detection Dashboard")
st.caption(
    "Analytics powered by dbt marts in the `analytics` schema. "
    "Airflow `dbt_marts_refresh` rebuilds marts on a schedule; use Refresh for immediate updates."
)

with st.sidebar:
    st.subheader("Data")
    st.caption(
        "Rebuild `analytics` marts from Postgres (on-demand). "
        "Scheduled rebuilds run via Airflow `dbt_marts_refresh`."
    )
    if st.button("Refresh data", type="primary", use_container_width=True):
        with st.spinner("Running dbt run…"):
            ok, log = refresh.rebuild_marts()
        st.session_state["dbt_refresh_log"] = log
        if ok:
            refresh.clear_caches()
            st.session_state["dbt_refresh_failed"] = False
            st.success("Analytics marts rebuilt.")
            st.rerun()
        else:
            st.session_state["dbt_refresh_failed"] = True
            st.error("dbt run failed.")
    if log := st.session_state.get("dbt_refresh_log"):
        with st.expander(
            "Last dbt output",
            expanded=st.session_state.get("dbt_refresh_failed", False),
        ):
            st.code(log[-8000:] if len(log) > 8000 else log)

tab_general, tab_velocity = st.tabs(["General Overview", "Velocity Deep-Dive"])

with tab_general:
    general.render()

with tab_velocity:
    velocity.render()
