"""Dashboard 2 — Velocity Fraud Deep-Dive."""

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
    st.header("Velocity Fraud Deep-Dive")
    st.caption(
        "Who is triggering velocity rules, at what speed, "
        "and does it point to a coordinated attack?"
    )

    if not data.mart_exists("mart_velocity_kpis"):
        st.warning(
            "Velocity analytics marts not found. Run `dbt run --profiles-dir .` in "
            "`dbt_fraud/` after Postgres has velocity-flagged transactions "
            "(VELOCITY_1H in flag_reasons)."
        )
        return

    kpi = data.load_mart("mart_velocity_kpis").iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Velocity Fraud Flags", int(kpi["velocity_fraud_count"] or 0))
    c2.metric("Velocity Share of Fraud", f"{kpi['velocity_fraud_share_pct'] or 0:.1f}%")
    c3.metric("Sum Velocity Fraud Amount", f"${kpi['sum_velocity_fraud_amount_usd'] or 0:,.2f}")
    c4.metric(
        "Avg Time Between Flagged Txns",
        f"{kpi['avg_time_between_flagged_sec'] or 0:.1f}s",
    )
    c5.metric("Unique Velocity Users", int(kpi["unique_velocity_users"] or 0))

    st.divider()

    st.subheader("Speed Profile & User Exposure")
    r1c1, r1c2, r1c3 = st.columns(3)

    buckets_df = data.load_mart("mart_velocity_buckets")
    vel_users = data.load_mart("mart_top_users_velocity")

    with r1c1:
        if buckets_df.empty:
            st.info("No velocity fraud in the lookback window.")
        else:
            st.plotly_chart(
                charts.vertical_bar(
                    buckets_df,
                    x="velocity_bucket",
                    y="fraud_count",
                    title="Flagged Transactions by Velocity Bucket",
                ),
                use_container_width=True,
            )

    with r1c2:
        if vel_users.empty:
            st.info("No velocity fraud users.")
        else:
            st.plotly_chart(charts.velocity_users_bar(vel_users.head(10)), use_container_width=True)

    with r1c3:
        if vel_users.empty:
            st.info("No velocity amount data.")
        else:
            amount_df = vel_users.sort_values("velocity_fraud_amount_usd", ascending=True).head(10)
            st.plotly_chart(
                charts.horizontal_bar(
                    amount_df,
                    x="velocity_fraud_amount_usd",
                    y="user_id",
                    title="Top Users by Velocity-Flagged Amount",
                ),
                use_container_width=True,
            )

    st.divider()
    st.subheader("Geographic Concentration (Velocity)")
    g1, g2 = st.columns(2)

    count_df = data.load_mart("mart_country_velocity_count")
    rate_df = data.load_mart("mart_country_velocity_rate")

    with g1:
        if count_df.empty:
            st.info("No velocity fraud counts by country.")
        else:
            st.plotly_chart(
                charts.vertical_bar(
                    count_df.head(10),
                    x="country",
                    y="velocity_fraud_count",
                    title="Top Countries by Velocity Fraud Count",
                ),
                use_container_width=True,
            )

    with g2:
        if rate_df.empty:
            st.info("No countries with ≥3 txns for velocity rate ranking.")
        else:
            st.plotly_chart(
                charts.vertical_bar(
                    rate_df.head(10),
                    x="country",
                    y="velocity_fraud_rate_pct",
                    title="Top Countries by Velocity Fraud Rate",
                ),
                use_container_width=True,
            )

    st.divider()
    st.subheader("Attack Pattern Analysis")
    p1, p2 = st.columns(2)

    scatter_df = data.load_mart("mart_velocity_scatter")
    with p1:
        if scatter_df.empty:
            st.info("No velocity scatter data (need consecutive txns per user).")
        else:
            st.plotly_chart(charts.velocity_scatter(scatter_df), use_container_width=True)

    with p2:
        share_granularity = _trend_controls("velocity_share")
        share_df = data.load_trend(data.VELOCITY_SHARE_TREND_MARTS, share_granularity)
        if share_df.empty:
            st.info("No velocity share trend data.")
        else:
            st.plotly_chart(charts.velocity_share_trend(share_df), use_container_width=True)

    st.divider()
    st.subheader("Behavioural Timing Patterns")
    b1, b2 = st.columns(2)

    heatmap_df = data.load_mart("mart_velocity_heatmap")
    interval_df = data.load_mart("mart_repeat_interval")

    with b1:
        if heatmap_df.empty:
            st.info("No velocity heatmap data.")
        else:
            st.plotly_chart(charts.velocity_heatmap(heatmap_df), use_container_width=True)

    with b2:
        if interval_df.empty:
            st.info("No repeat interval data.")
        else:
            st.plotly_chart(charts.interval_histogram(interval_df), use_container_width=True)

    st.divider()
    st.subheader("Time Trend (Velocity)")
    trend_granularity = _trend_controls("velocity")
    trend_df = data.load_trend(data.VELOCITY_TREND_MARTS, trend_granularity)
    if trend_df.empty:
        st.info("No velocity trend data yet.")
    else:
        st.plotly_chart(
            charts.fraud_trend_dual_axis(
                trend_df,
                count_label="Velocity fraud count",
                rate_label="Velocity fraud rate (% of all txns)",
                title="Velocity-Flagged Transactions Over Time",
            ),
            use_container_width=True,
        )
