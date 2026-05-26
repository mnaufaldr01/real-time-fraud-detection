"""Streamlit fraud detection dashboard — General + Velocity views powered by dbt marts."""

from __future__ import annotations

from datetime import timedelta

import streamlit as st

from dashboard import data, refresh
from dashboard.views import general, velocity

st.set_page_config(page_title="Fraud Detection Dashboard", layout="wide", page_icon="🛡️")

st.title("Real-Time Fraud Detection Dashboard")
st.caption(
    "Analytics powered by dbt marts in the `analytics` schema. "
    "Airflow `dbt_marts_refresh` rebuilds marts on a schedule; charts reload automatically."
)


@st.fragment(run_every=timedelta(seconds=data.AUTO_REFRESH_SECONDS))
def _poll_mart_updates() -> None:
    """Detect Airflow dbt runs by watching KPI mart fingerprints."""
    fingerprint = data.get_marts_fingerprint()
    previous = st.session_state.get("marts_fingerprint")
    if previous is None:
        st.session_state["marts_fingerprint"] = fingerprint
        return
    if fingerprint != previous:
        st.session_state["marts_fingerprint"] = fingerprint
        refresh.reload_charts()
        st.rerun()


with st.sidebar:
    st.subheader("Data")
    st.caption(
        f"Polls Postgres every {data.AUTO_REFRESH_SECONDS}s for Airflow dbt rebuilds. "
        "Use the buttons below for immediate actions."
    )
    _poll_mart_updates()

    if st.button("Reload charts", type="primary", use_container_width=True):
        st.session_state["marts_fingerprint"] = data.get_marts_fingerprint()
        refresh.reload_charts()
        st.rerun()

    with st.expander("Run dbt locally"):
        st.caption(
            "Optional — runs `dbt run` on this machine. "
            "Skip if Airflow `dbt_marts_refresh` is already enabled."
        )
        if st.button("Run dbt & reload", use_container_width=True):
            with st.spinner("Running dbt run…"):
                ok, log = refresh.rebuild_marts()
            st.session_state["dbt_refresh_log"] = log
            if ok:
                st.session_state["marts_fingerprint"] = data.get_marts_fingerprint()
                refresh.reload_charts()
                st.session_state["dbt_refresh_failed"] = False
                st.success("Analytics marts rebuilt.")
                st.rerun()
            else:
                st.session_state["dbt_refresh_failed"] = True
                st.error("dbt run failed.")

    if log := st.session_state.get("dbt_refresh_log"):
        with st.expander(
            "Last local dbt output",
            expanded=st.session_state.get("dbt_refresh_failed", False),
        ):
            st.code(log[-8000:] if len(log) > 8000 else log)

tab_general, tab_velocity = st.tabs(["General Overview", "Velocity Deep-Dive"])

with tab_general:
    general.render()

with tab_velocity:
    velocity.render()
