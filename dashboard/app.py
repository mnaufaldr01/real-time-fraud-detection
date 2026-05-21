"""Streamlit fraud detection dashboard (Tier 2)."""

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://fraud:fraud@localhost:5432/fraud_db")

st.set_page_config(page_title="Fraud Detection Dashboard", layout="wide")
st.title("Real-Time Fraud Detection Dashboard")


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


engine = get_engine()


def query_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


# KPIs
col1, col2, col3, col4 = st.columns(4)

kpi = query_df(
    """
    SELECT
        COUNT(*) AS total_tx,
        COUNT(*) FILTER (WHERE ff.is_fraud) AS fraud_count,
        COUNT(*) FILTER (WHERE ff.is_fraud) * 100.0 / NULLIF(COUNT(*), 0) AS fraud_rate,
        MAX(rs.scored_at) AS last_scored
    FROM transactions t
    LEFT JOIN fraud_flags ff ON ff.transaction_id = t.transaction_id
    LEFT JOIN risk_scores rs ON rs.transaction_id = t.transaction_id
    WHERE t.timestamp >= NOW() - INTERVAL '24 hours'
    """
).iloc[0]

col1.metric("Transactions (24h)", int(kpi["total_tx"] or 0))
col2.metric("Fraud Flags (24h)", int(kpi["fraud_count"] or 0))
col3.metric("Fraud Rate (24h)", f"{kpi['fraud_rate'] or 0:.2f}%")

if kpi["last_scored"]:
    lag_seconds = (datetime.now(timezone.utc) - kpi["last_scored"].replace(tzinfo=timezone.utc)).total_seconds()
    col4.metric("Consumer Lag (sec)", f"{lag_seconds:.0f}")
else:
    col4.metric("Consumer Lag (sec)", "N/A")

st.divider()

# Top flag reasons
st.subheader("Top Flag Reasons (24h)")
reasons_df = query_df(
    """
    SELECT reason, COUNT(*) AS cnt
    FROM fraud_flags ff,
         LATERAL jsonb_array_elements_text(ff.flag_reasons) AS reason
    WHERE ff.scored_at >= NOW() - INTERVAL '24 hours'
      AND ff.is_fraud = TRUE
    GROUP BY reason
    ORDER BY cnt DESC
    LIMIT 10
    """
)

if not reasons_df.empty:
    fig = px.bar(reasons_df, x="reason", y="cnt", title="Flag Reasons")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No fraud flags in the last 24 hours.")

# Recent flags table
st.subheader("Recent Fraud Flags")
recent = query_df(
    """
    SELECT t.transaction_id, t.user_id, t.amount, t.country,
           rs.final_score, ff.flag_reasons, ff.scored_at
    FROM fraud_flags ff
    JOIN transactions t ON t.transaction_id = ff.transaction_id
    JOIN risk_scores rs ON rs.transaction_id = ff.transaction_id
    WHERE ff.is_fraud = TRUE
    ORDER BY ff.scored_at DESC
    LIMIT 50
    """
)
st.dataframe(recent, use_container_width=True)

# Stream vs batch comparison
st.subheader("Stream vs Batch Score Comparison")
comparison = query_df(
    """
    SELECT rs.transaction_id, rs.final_score AS stream_score,
           rsh.final_score AS batch_score,
           ABS(rs.final_score - rsh.final_score) AS delta
    FROM risk_scores rs
    JOIN risk_scores_history rsh ON rsh.transaction_id = rs.transaction_id
    WHERE rsh.scored_at >= NOW() - INTERVAL '7 days'
    ORDER BY delta DESC
    LIMIT 20
    """
)
if not comparison.empty:
    st.dataframe(comparison, use_container_width=True)
else:
    st.info("Run the Airflow daily_rescore DAG to populate batch scores.")
