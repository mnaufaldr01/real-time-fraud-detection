"""Plotly chart builders for fraud dashboards."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# Plotly choropleth supports ISO-3, not ISO-2 (events store alpha-2 in `country`).
_ISO2_TO_ISO3: dict[str, str] = {
    "US": "USA",
    "GB": "GBR",
    "DE": "DEU",
    "FR": "FRA",
    "NL": "NLD",
    "AU": "AUS",
    "SG": "SGP",
    "ID": "IDN",
    "RU": "RUS",
    "CA": "CAN",
    "MX": "MEX",
    "BR": "BRA",
    "IN": "IND",
    "CN": "CHN",
    "JP": "JPN",
    "IT": "ITA",
    "ES": "ESP",
    "CH": "CHE",
    "SE": "SWE",
    "PL": "POL",
    "TR": "TUR",
    "SA": "SAU",
    "AE": "ARE",
    "ZA": "ZAF",
    "TH": "THA",
    "MY": "MYS",
    "PH": "PHL",
    "NZ": "NZL",
    "IE": "IRL",
    "BE": "BEL",
    "AT": "AUT",
    "PT": "PRT",
    "DK": "DNK",
    "FI": "FIN",
    "HK": "HKG",
    "KR": "KOR",
    "NO": "NOR",
    "VN": "VNM",
    "EG": "EGY",
    "NG": "NGA",
}


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
    fig.update_layout(legend_title_text="Status", xaxis_title="Currency", yaxis_title="Count")
    return fig


def horizontal_bar(df: pd.DataFrame, x: str, y: str, title: str, text: str | None = None) -> go.Figure:
    plot_df = df.sort_values(x, ascending=True)
    fig = px.bar(plot_df, x=x, y=y, orientation="h", title=title, text=text)
    if text:
        fig.update_traces(textposition="outside")
    return fig


def vertical_bar(df: pd.DataFrame, x: str, y: str, title: str) -> go.Figure:
    return px.bar(df, x=x, y=y, title=title)


def fraud_trend_dual_axis(
    df: pd.DataFrame,
    date_col: str = "report_date",
    count_label: str = "Fraud flagged count",
    rate_label: str = "Fraud rate (%)",
    title: str = "Fraud Flagged Over Time",
) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=df[date_col],
            y=df["fraud_count"],
            name=count_label,
            marker_color="#e74c3c",
            opacity=0.75,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df[date_col],
            y=df["fraud_rate_pct"],
            name=rate_label,
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
                    name="Anomaly (>2σ rolling)",
                    marker=dict(color="#f39c12", size=14, symbol="diamond"),
                ),
                secondary_y=True,
            )
    fig.update_layout(
        title=title,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(title_text=count_label, secondary_y=False)
    fig.update_yaxes(title_text=rate_label, secondary_y=True)
    return fig


def choropleth_fraud_count(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure().update_layout(title="Fraud Flag Count by Country")

    plot_df = df.copy()
    plot_df["iso3"] = plot_df["country"].str.upper().map(_ISO2_TO_ISO3)
    plot_df = plot_df.dropna(subset=["iso3"])
    if plot_df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Fraud Flag Count by Country",
            annotations=[
                dict(
                    text="No mappable country codes in data",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                )
            ],
        )
        return fig

    fig = px.choropleth(
        plot_df,
        locations="iso3",
        locationmode="ISO-3",
        color="fraud_count",
        hover_name="country",
        hover_data={"fraud_count": True, "iso3": False},
        color_continuous_scale="Reds",
        title="Fraud Flag Count by Country",
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
        title="Fraud Flag Count by Rule / Reason Type",
        labels={"reason_count": "Flag count", "reason": "Rule / reason"},
    )


def velocity_scatter(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df,
        x="velocity_seconds",
        y="amount_usd",
        color="country",
        hover_data=["user_id", "transaction_id"],
        title="Transaction Amount vs Velocity (seconds between txns)",
        labels={"velocity_seconds": "Velocity (sec)", "amount_usd": "Amount (USD)"},
    )
    if not df.empty:
        x_mid = df["velocity_seconds"].median()
        y_mid = df["amount_usd"].median()
        fig.add_vline(x=x_mid, line_dash="dash", line_color="#95a5a6", opacity=0.6)
        fig.add_hline(y=y_mid, line_dash="dash", line_color="#95a5a6", opacity=0.6)
        fig.add_annotation(
            x=df["velocity_seconds"].quantile(0.15),
            y=df["amount_usd"].quantile(0.85),
            text="Priority Investigation",
            showarrow=False,
            font=dict(color="#c0392b", size=13, family="Arial Black"),
            bgcolor="rgba(255,255,255,0.7)",
        )
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
        title="Velocity Fraud Flags by Hour × Day of Week",
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    return fig


def velocity_share_trend(df: pd.DataFrame, date_col: str = "report_date") -> go.Figure:
    fig = px.line(
        df,
        x=date_col,
        y="velocity_fraud_share_pct",
        markers=True,
        title="Velocity Fraud as % of Total Fraud Over Time",
        labels={
            "velocity_fraud_share_pct": "Velocity share of fraud (%)",
            date_col: "Period",
        },
    )
    fig.update_traces(line_color="#8e44ad", line_width=2)
    return fig


def interval_histogram(df: pd.DataFrame) -> go.Figure:
    return px.bar(
        df,
        x="interval_bucket",
        y="interval_count",
        title="Time Between Consecutive Velocity-Flagged Transactions",
        labels={"interval_bucket": "Gap (seconds)", "interval_count": "Frequency"},
    )


def velocity_users_bar(df: pd.DataFrame) -> go.Figure:
    plot_df = df.sort_values("velocity_fraud_count", ascending=True).copy()
    plot_df["label"] = plot_df.apply(
        lambda r: f"{r['velocity_fraud_count']} (avg {r['avg_velocity_seconds']}s)",
        axis=1,
    )
    fig = px.bar(
        plot_df,
        x="velocity_fraud_count",
        y="user_id",
        orientation="h",
        title="Top Users by Velocity-Flagged Transaction Count",
        text="label",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="Velocity-flagged count", yaxis_title="User")
    return fig
