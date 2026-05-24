"""Streamlit fraud detection dashboard — General + Velocity views powered by dbt marts."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard.views import general, velocity

st.set_page_config(page_title="Fraud Detection Dashboard", layout="wide", page_icon="🛡️")

st.title("Real-Time Fraud Detection Dashboard")
st.caption("Analytics powered by dbt marts in the `analytics` schema.")

tab_general, tab_velocity = st.tabs(["General Overview", "Velocity Deep-Dive"])

with tab_general:
    general.render()

with tab_velocity:
    velocity.render()
