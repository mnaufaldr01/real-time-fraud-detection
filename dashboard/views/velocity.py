"""Dashboard 2 — Velocity Fraud Deep-Dive."""

from __future__ import annotations

import streamlit as st

from dashboard import charts, data


def render() -> None:
    st.header("Velocity Fraud Deep-Dive")
    st.caption(
        "Who is triggering velocity rules, at what speed, "
        "and is it a real pattern or a false positive?"
    )

    if not data.mart_exists("mart_velocity_buckets"):
        st.warning(
            "Velocity analytics marts not found. Run `make dbt-run` after Postgres has "
            "velocity-flagged transactions (VELOCITY_1H in flag_reasons)."
        )
        return

    st.subheader("How fast + Who?")
    r1c1, r1c2 = st.columns([1, 1])

    buckets_df = data.load_mart("mart_velocity_buckets")
    with r1c1:
        if buckets_df.empty:
            st.info("No velocity fraud in the last 30 days.")
        else:
            st.plotly_chart(
                charts.horizontal_bar(
                    buckets_df,
                    x="fraud_count",
                    y="velocity_bucket",
                    title="Velocity Fraud by Time-Since-Previous-Txn Bucket",
                ),
                use_container_width=True,
            )
            st.caption(
                "X-axis: seconds/minutes since the user's previous transaction. "
                "Under 5s suggests automated card testing."
            )

    with r1c2:
        vel_users = data.load_mart("mart_top_users_velocity")
        if vel_users.empty:
            st.info("No velocity fraud users.")
        else:
            st.markdown("**Top users — velocity fraud**")
            st.dataframe(
                vel_users.rename(
                    columns={
                        "velocity_fraud_count": "Velocity flags",
                        "velocity_fraud_amount_usd": "Flagged amount (USD)",
                        "avg_velocity_seconds": "Avg velocity (sec)",
                    }
                ),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Flagged amount (USD)": st.column_config.NumberColumn(format="$%.2f"),
                    "Avg velocity (sec)": st.column_config.NumberColumn(format="%.1f"),
                },
            )

    st.divider()
    st.subheader("Where?")
    g1, g2 = st.columns(2)

    rate_df = data.load_mart("mart_country_velocity_rate")
    count_df = data.load_mart("mart_country_velocity_count")

    with g1:
        if rate_df.empty:
            st.info("Not enough velocity data by country.")
        else:
            st.plotly_chart(
                charts.horizontal_bar(
                    rate_df.head(10),
                    x="velocity_fraud_rate_pct",
                    y="country",
                    title="Top Countries by Velocity Fraud Rate",
                ),
                use_container_width=True,
            )

    with g2:
        if count_df.empty:
            st.info("No velocity fraud counts by country.")
        else:
            st.plotly_chart(
                charts.horizontal_bar(
                    count_df.head(10),
                    x="velocity_fraud_count",
                    y="country",
                    title="Top Countries by Velocity Fraud Count",
                ),
                use_container_width=True,
            )

    flow_df = data.load_mart("mart_origin_dest_flow")
    if flow_df.empty:
        st.info("No origin→destination flows for velocity fraud.")
    else:
        st.plotly_chart(charts.sankey_origin_dest(flow_df), use_container_width=True)

    st.divider()
    st.subheader("What pattern?")

    scatter_df = data.load_mart("mart_velocity_scatter")
    if scatter_df.empty:
        st.info("No velocity scatter data (need consecutive txns per user).")
    else:
        st.plotly_chart(charts.velocity_scatter(scatter_df), use_container_width=True)
        st.caption(
            "Top-left quadrant (high amount, low velocity seconds) = highest-risk zone."
        )

    p1, p2 = st.columns(2)

    share_trend = data.load_mart("mart_velocity_share_trend")
    with p1:
        if share_trend.empty:
            st.info("No velocity share trend data.")
        else:
            st.plotly_chart(charts.velocity_share_trend(share_trend), use_container_width=True)

    heatmap_df = data.load_mart("mart_velocity_heatmap")
    with p2:
        if heatmap_df.empty:
            st.info("No velocity heatmap data.")
        else:
            st.plotly_chart(charts.velocity_heatmap(heatmap_df), use_container_width=True)

    st.subheader("Repeat interval distribution")
    interval_df = data.load_mart("mart_repeat_interval")
    if interval_df.empty:
        st.info("No repeat intervals between flagged velocity txns.")
    else:
        st.plotly_chart(
            charts.horizontal_bar(
                interval_df,
                x="interval_count",
                y="interval_bucket",
                title="Gap Between Consecutive Velocity-Flagged Txns",
            ),
            use_container_width=True,
        )
        st.caption("A spike at exactly 3–5 seconds often indicates bot-like behaviour.")
