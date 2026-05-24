"""Plotly chart builders for fraud dashboards."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def currency_stacked_bar(df: pd.DataFrame) -> go.Figure:
    melted = df.melt(
        id_vars=["currency"],
        value_vars=["legitimate_count", "flagged_count"],
        var_name="status",
        value_name="count",
    )
    melted["status"] = melted["status"].map(
        {"legitimate_count": "Legitimate", "flagged_count": "Flagged"}
    )
    fig = px.bar(
        melted,
        x="currency",
        y="count",
        color="status",
        barmode="stack",
        title="Legitimate vs Flagged Transactions by Currency",
        color_discrete_map={"Legitimate": "#2ecc71", "Flagged": "#e74c3c"},
    )
    fig.update_layout(legend_title_text="Status")
    return fig


def horizontal_bar(df: pd.DataFrame, x: str, y: str, title: str) -> go.Figure:
    plot_df = df.sort_values(x, ascending=True)
    return px.bar(plot_df, x=x, y=y, orientation="h", title=title)


def fraud_trend_dual_axis(df: pd.DataFrame, date_col: str = "report_date") -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=df[date_col],
            y=df["fraud_count"],
            name="Fraud count",
            marker_color="#e74c3c",
            opacity=0.7,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df[date_col],
            y=df["fraud_rate_pct"],
            name="Fraud rate (%)",
            mode="lines+markers",
            line=dict(color="#3498db", width=2),
        ),
        secondary_y=True,
    )
    if "is_anomaly" in df.columns:
        anomalies = df[df["is_anomaly"]]
        if not anomalies.empty:
            fig.add_trace(
                go.Scatter(
                    x=anomalies[date_col],
                    y=anomalies["fraud_rate_pct"],
                    mode="markers",
                    name="Anomaly (>2σ)",
                    marker=dict(color="#f39c12", size=12, symbol="diamond"),
                ),
                secondary_y=True,
            )
    fig.update_layout(
        title="Fraud Trend — Count (bars) vs Rate (line)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(title_text="Fraud count", secondary_y=False)
    fig.update_yaxes(title_text="Fraud rate (%)", secondary_y=True)
    return fig


def choropleth_fraud_rate(df: pd.DataFrame) -> go.Figure:
    fig = px.choropleth(
        df,
        locations="country",
        locationmode="ISO-2",
        color="fraud_rate_pct",
        hover_name="country",
        hover_data={"total_tx": True, "fraud_count": True, "fraud_rate_pct": ":.2f"},
        color_continuous_scale="Reds",
        title="Fraud Rate by Country (min 3 txns)",
    )
    fig.update_geos(showcoastlines=True, projection_type="natural earth")
    return fig


def flag_reasons_bar(df: pd.DataFrame) -> go.Figure:
    plot_df = df.sort_values("reason_count", ascending=True)
    return px.bar(
        plot_df,
        x="reason_count",
        y="reason",
        orientation="h",
        title="Fraud Breakdown by Rule / Reason Type",
        labels={"reason_count": "Count", "reason": "Reason"},
    )


def merchant_dual_metric(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    plot_df = df.head(10)
    fig.add_trace(
        go.Bar(x=plot_df["merchant_id"], y=plot_df["fraud_count"], name="Fraud count"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df["merchant_id"],
            y=plot_df["fraud_rate_pct"],
            name="Fraud rate (%)",
            mode="lines+markers",
            line=dict(color="#e67e22"),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Top Merchants — Fraud Count vs Fraud Rate",
        xaxis_title="Merchant",
    )
    fig.update_yaxes(title_text="Fraud count", secondary_y=False)
    fig.update_yaxes(title_text="Fraud rate (%)", secondary_y=True)
    return fig


def velocity_scatter(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df,
        x="velocity_seconds",
        y="amount_usd",
        color="country",
        hover_data=["user_id", "transaction_id"],
        title="Amount vs Velocity (seconds since previous txn)",
        labels={"velocity_seconds": "Velocity (sec)", "amount_usd": "Amount (USD)"},
    )
    if not df.empty:
        x_mid = df["velocity_seconds"].median()
        y_mid = df["amount_usd"].median()
        fig.add_vline(x=x_mid, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_hline(y=y_mid, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_annotation(
            x=df["velocity_seconds"].quantile(0.1),
            y=df["amount_usd"].quantile(0.9),
            text="High amount + fast velocity",
            showarrow=False,
            font=dict(color="#c0392b"),
        )
    return fig


def sankey_origin_dest(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    origins = sorted(df["origin_country"].unique())
    dests = sorted(df["destination_country"].unique())
    labels = [f"{o} (card)" for o in origins] + [f"{d} (IP)" for d in dests]
    origin_idx = {o: i for i, o in enumerate(origins)}
    dest_idx = {d: i + len(origins) for i, d in enumerate(dests)}

    fig = go.Figure(
        go.Sankey(
            node=dict(label=labels, pad=15, thickness=20),
            link=dict(
                source=[origin_idx[o] for o in df["origin_country"]],
                target=[dest_idx[d] for d in df["destination_country"]],
                value=df["txn_count"].tolist(),
            ),
        )
    )
    fig.update_layout(title="Velocity Fraud — Card Country → IP Country Flow")
    return fig


def velocity_heatmap(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    pivot = df.pivot_table(
        index="day_of_week",
        columns="hour_of_day",
        values="velocity_fraud_count",
        fill_value=0,
    )
    pivot.index = [DAY_LABELS[int(i)] for i in pivot.index]
    fig = px.imshow(
        pivot,
        labels=dict(x="Hour of day", y="Day of week", color="Velocity flags"),
        title="Velocity Fraud Heatmap — Hour × Day of Week",
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    return fig


def velocity_share_trend(df: pd.DataFrame) -> go.Figure:
    fig = px.line(
        df,
        x="report_date",
        y="velocity_fraud_share_pct",
        markers=True,
        title="Velocity Fraud as % of Total Fraud Over Time",
        labels={"velocity_fraud_share_pct": "Velocity fraud share (%)", "report_date": "Date"},
    )
    fig.update_traces(line_color="#8e44ad")
    return fig
