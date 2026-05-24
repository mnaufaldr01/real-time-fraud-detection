"""Dashboard 1 — General Fraud Overview."""

from __future__ import annotations

import streamlit as st

from dashboard import charts, data


def _trend_controls(key_prefix: str) -> str:
    return st.radio(
        "Granularity",
        ["Yearly", "Monthly", "Daily"],
        horizontal=True,
        key=f"{key_prefix}_granularity",
    )


def render() -> None:
    st.header("General Fraud Overview")
    st.caption("How bad is our fraud problem, and where is it concentrated?")

    if not data.mart_exists("mart_general_kpis"):
        st.warning(
            "Analytics marts not found. Run `make dbt-run` after Postgres has transaction data."
        )
        return

    kpi = data.load_mart("mart_general_kpis").iloc[0]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Transactions", int(kpi["total_tx"] or 0))
    c2.metric("Fraud Flagged Count", int(kpi["fraud_count"] or 0))
    c3.metric("Fraud Rate", f"{kpi['fraud_rate_pct'] or 0:.2f}%")
    c4.metric("Sum Fraud Amount", f"${kpi['sum_fraud_amount_usd'] or 0:,.2f}")
    c5.metric("Avg Fraud Txn Value", f"${kpi['avg_fraud_txn_value_usd'] or 0:,.2f}")
    c6.metric(
        "Flagged-to-Reviewed",
        f"{kpi['flagged_to_review_ratio_pct'] or 0:.1f}%",
        help="Review-queue flags as % of total fraud flags (operational load)",
    )

    st.divider()

    st.subheader("Row 1 — Currency & User Exposure")
    r1_left, r1_right = st.columns([1, 2])

    with r1_left:
        currency_df = data.load_mart("mart_currency_breakdown")
        if currency_df.empty:
            st.info("No currency data.")
        else:
            st.plotly_chart(charts.currency_stacked_bar(currency_df), use_container_width=True)

    with r1_right:
        users_df = data.load_mart("mart_top_users_fraud")
        if users_df.empty:
            st.info("No fraud users in the lookback window.")
        else:
            u1, u2 = st.columns(2)
            with u1:
                st.plotly_chart(
                    charts.top_users_fraud_bar(
                        users_df,
                        metric="fraud_count",
                        title="Top Users by Fraud-Flagged Count",
                    ),
                    use_container_width=True,
                )
            with u2:
                st.plotly_chart(
                    charts.top_users_fraud_bar(
                        users_df,
                        metric="fraud_amount_usd",
                        title="Top Users by Fraud-Flagged Amount (USD)",
                    ),
                    use_container_width=True,
                )

    st.divider()
    st.subheader("Row 2 — Merchant Exposure")
    m1, m2 = st.columns(2)

    merchant_count = data.load_mart("mart_merchant_fraud_by_count")
    merchant_rate = data.load_mart("mart_merchant_fraud_by_rate")

    with m1:
        if merchant_count.empty:
            st.info("No merchant fraud counts.")
        else:
            st.plotly_chart(
                charts.horizontal_bar(
                    merchant_count.head(10),
                    x="fraud_count",
                    y="merchant_id",
                    title="Top Merchants by Fraud-Flagged Count",
                ),
                use_container_width=True,
            )

    with m2:
        if merchant_rate.empty:
            st.info("No merchants with ≥3 transactions for rate ranking.")
        else:
            st.plotly_chart(
                charts.horizontal_bar(
                    merchant_rate.head(10),
                    x="fraud_rate_pct",
                    y="merchant_id",
                    title="Top Merchants by Fraud Rate (≥3 txns)",
                ),
                use_container_width=True,
            )

    st.divider()
    st.subheader("Row 3 — Geographic Concentration")
    g1, g2 = st.columns(2)

    count_df = data.load_mart("mart_country_fraud_count")
    rate_df = data.load_mart("mart_country_fraud_rate")

    with g1:
        if count_df.empty:
            st.info("No country fraud counts.")
        else:
            st.plotly_chart(
                charts.vertical_bar(
                    count_df.head(10),
                    x="country",
                    y="fraud_count",
                    title="Top Countries by Fraud Count",
                ),
                use_container_width=True,
            )

    with g2:
        if rate_df.empty:
            st.info("No countries with ≥3 txns for rate ranking.")
        else:
            st.plotly_chart(
                charts.vertical_bar(
                    rate_df.head(10),
                    x="country",
                    y="fraud_rate_pct",
                    title="Top Countries by Fraud Rate",
                ),
                use_container_width=True,
            )

    st.divider()
    st.subheader("Row 4 — Fraud by Rule Type")
    reasons_df = data.load_mart("mart_flag_reasons")
    if reasons_df.empty:
        st.info("No rule-level flag reasons recorded yet.")
    else:
        st.plotly_chart(charts.flag_reasons_bar(reasons_df), use_container_width=True)

    st.divider()
    st.subheader("Row 5 — Time Trend")
    granularity = _trend_controls("general")
    trend_df = data.load_trend(data.GENERAL_TREND_MARTS, granularity)
    if trend_df.empty:
        st.info("No trend data yet.")
    else:
        st.plotly_chart(
            charts.fraud_trend_dual_axis(trend_df, title="Fraud Flagged Over Time"),
            use_container_width=True,
        )
