"""Dashboard 1 — General Fraud Overview."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from dashboard import charts, data


def render() -> None:
    st.header("General Fraud Overview")
    st.caption('How bad is our fraud problem, and where is it concentrated?')

    if not data.mart_exists("mart_general_kpis"):
        st.warning(
            "Analytics marts not found. Run `make dbt-run` (or `dbt run` in `dbt_fraud/`) "
            "after starting Postgres with transaction data."
        )
        return

    kpi = data.load_mart("mart_general_kpis").iloc[0]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Transactions (24h)", int(kpi["total_tx"] or 0))
    c2.metric("Fraud Flags (24h)", int(kpi["fraud_count"] or 0))
    c3.metric("Fraud Rate (24h)", f"{kpi['fraud_rate_pct'] or 0:.2f}%")
    c4.metric(
        "Avg Fraud Txn Value",
        f"${kpi['avg_fraud_txn_value_usd'] or 0:,.2f}",
    )
    c5.metric(
        "Flagged-to-Review Ratio",
        f"{kpi['flagged_to_review_ratio_pct'] or 0:.1f}%",
        help="Review queue (requires_user_confirmation) as % of fraud flags",
    )
    if kpi.get("last_scored_at") and pd.notna(kpi["last_scored_at"]):
        last_scored = kpi["last_scored_at"]
        if last_scored.tzinfo is None:
            last_scored = last_scored.replace(tzinfo=timezone.utc)
        lag = (datetime.now(timezone.utc) - last_scored).total_seconds()
        c6.metric("Consumer Lag (sec)", f"{lag:.0f}")
    else:
        c6.metric("Consumer Lag (sec)", "N/A")

    st.divider()

    st.subheader("Where (currency) + Who?")
    r1c1, r1c2 = st.columns([1, 1])

    currency_df = data.load_mart("mart_currency_breakdown")
    with r1c1:
        if currency_df.empty:
            st.info("No currency data in the last 24 hours.")
        else:
            st.plotly_chart(charts.currency_stacked_bar(currency_df), use_container_width=True)

    with r1c2:
        users_df = data.attach_user_sparklines(data.load_mart("mart_top_users_fraud"))
        if users_df.empty:
            st.info("No fraud users in the last 30 days.")
        else:
            st.markdown("**Top users by fraud activity**")
            display = users_df[
                ["user_id", "fraud_count", "fraud_amount_usd", "sparkline"]
            ].rename(
                columns={
                    "fraud_count": "Fraud txns",
                    "fraud_amount_usd": "Fraud amount (USD)",
                }
            )
            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "sparkline": st.column_config.LineChartColumn(
                        "Activity (14d)",
                        width="medium",
                        y_min=0,
                    ),
                    "Fraud amount (USD)": st.column_config.NumberColumn(format="$%.2f"),
                },
            )

    st.subheader("Merchants")
    merchant_df = data.load_mart("mart_merchant_fraud")
    if merchant_df.empty:
        st.info("No merchant fraud data.")
    else:
        st.plotly_chart(charts.merchant_dual_metric(merchant_df), use_container_width=True)

    st.divider()
    st.subheader("Where (geography)?")
    g1, g2 = st.columns(2)

    rate_df = data.load_mart("mart_country_fraud_rate")
    count_df = data.load_mart("mart_country_fraud_count")

    with g1:
        if rate_df.empty:
            st.info("Not enough country data (need ≥3 txns per country).")
        else:
            top_rate = rate_df.head(10)
            st.plotly_chart(
                charts.horizontal_bar(
                    top_rate,
                    x="fraud_rate_pct",
                    y="country",
                    title="Top Countries by Fraud Rate",
                ),
                use_container_width=True,
            )

    with g2:
        if count_df.empty:
            st.info("No country fraud counts.")
        else:
            st.plotly_chart(
                charts.horizontal_bar(
                    count_df.head(10),
                    x="fraud_count",
                    y="country",
                    title="Top Countries by Fraud Count (absolute volume)",
                ),
                use_container_width=True,
            )

    if not rate_df.empty:
        st.plotly_chart(charts.choropleth_fraud_rate(rate_df), use_container_width=True)

    st.divider()
    st.subheader("When? — Fraud trend")
    granularity = st.radio(
        "Granularity",
        ["Daily", "Monthly"],
        horizontal=True,
        key="general_trend_granularity",
    )
    if granularity == "Daily":
        trend_df = data.load_mart("mart_fraud_trend_daily")
    else:
        trend_df = data.load_mart("mart_fraud_trend_monthly")
        trend_df = trend_df.rename(
            columns={"report_month": "report_date", "fraud_rate_pct": "fraud_rate_pct"}
        )

    if trend_df.empty:
        st.info("No trend data yet.")
    else:
        st.plotly_chart(
            charts.fraud_trend_dual_axis(trend_df),
            use_container_width=True,
        )

    st.divider()
    st.subheader("What kind of fraud?")
    reasons_df = data.load_mart("mart_flag_reasons")
    if reasons_df.empty:
        st.info("No rule-level flag reasons recorded yet.")
    else:
        st.plotly_chart(charts.flag_reasons_bar(reasons_df), use_container_width=True)

    with st.expander("Recent fraud flags & stream vs batch"):
        recent = data.load_mart("mart_recent_fraud_flags")
        if not recent.empty:
            st.dataframe(recent, use_container_width=True, hide_index=True)
        comparison = data.load_mart("mart_stream_vs_batch")
        if not comparison.empty:
            st.markdown("**Stream vs batch score comparison**")
            st.dataframe(comparison, use_container_width=True, hide_index=True)
        elif recent.empty:
            st.info("No recent fraud flags.")
