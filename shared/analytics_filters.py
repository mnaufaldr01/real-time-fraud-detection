"""Date-filtered analytics queries over intermediate dbt models."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import text

from shared import analytics_marts as marts

LOOKBACK_DAYS = int(os.getenv("ANALYTICS_LOOKBACK_DAYS", "520"))
EVENTS = "intermediate.int_scored_events"
VELOCITY_EVENTS = "intermediate.int_velocity_fraud_events"
VELOCITY_INTERVALS = "intermediate.int_velocity_repeat_intervals"

FLAG_REASON_EXCLUSIONS = (
    "HARD_DECLINE",
    "ML_STRONG_SUSPECT",
    "RULE_STRONG_SUSPECT",
    "ML_SOFT",
    "RULE_SOFT",
    "ANOMALY_SOFT",
    "MULTI_SIGNAL_REVIEW",
    "SOFT_SIGNAL_OBSERVED",
    "ML_REVIEW",
    "RULE_REVIEW",
    "HIGH_ANOMALY",
    "OUT_OF_SCOPE",
)


def _window(year: int | None, month: int | None) -> tuple[str, dict[str, Any]]:
    if year is None:
        return (
            f"event_at >= current_timestamp - ({LOOKBACK_DAYS} || ' days')::interval",
            {},
        )

    start = date(year, month or 1, 1)
    if month is None:
        end = date(year + 1, 1, 1)
    elif month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    return (
        "event_at >= :window_start AND event_at < :window_end",
        {"window_start": start.isoformat(), "window_end": end.isoformat()},
    )


def _query_df(sql: str, params: dict[str, Any]) -> pd.DataFrame:
    engine = marts.get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def _records(sql: str, year: int | None, month: int | None) -> list[dict]:
    clause, params = _window(year, month)
    df = _query_df(sql.format(window_clause=clause), params)
    return marts.df_to_records(df)


def _first_row(sql: str, year: int | None, month: int | None) -> dict | None:
    records = _records(sql, year, month)
    return records[0] if records else None


def filter_trend_df(
    df: pd.DataFrame,
    year: int | None,
    month: int | None,
) -> pd.DataFrame:
    if year is None or df.empty:
        return df

    parsed = df.copy()
    parsed["_report_dt"] = pd.to_datetime(parsed["report_date"])
    if month is not None:
        mask = (parsed["_report_dt"].dt.year == year) & (parsed["_report_dt"].dt.month == month)
    else:
        mask = parsed["_report_dt"].dt.year == year
    return parsed.loc[mask].drop(columns=["_report_dt"]).reset_index(drop=True)


def load_trend_filtered(
    mart_map: dict[str, str],
    granularity: str,
    year: int | None = None,
    month: int | None = None,
) -> pd.DataFrame:
    df = marts.load_trend(mart_map, granularity)
    return filter_trend_df(df, year, month)


def general_kpis(year: int | None = None, month: int | None = None) -> dict | None:
    if year is None:
        return marts.df_first_row(marts.load_mart("mart_general_kpis"))

    sql = f"""
        select
            count(*) as total_tx,
            count(*) filter (where is_flagged) as flagged_count,
            count(*) filter (where is_fraud) as fraud_count,
            round(
                count(*) filter (where is_fraud) * 100.0 / nullif(count(*), 0),
                2,
            ) as fraud_rate_pct,
            round(coalesce(sum(amount_usd) filter (where is_fraud), 0), 2) as sum_fraud_amount_usd,
            round(
                count(*) filter (where requires_user_confirmation) * 100.0
                / nullif(
                    count(*) filter (where requires_user_confirmation)
                    + count(*) filter (where is_fraud),
                    0
                ),
                2
            ) as review_share_of_actions_pct
        from {EVENTS}
        where {{window_clause}}
    """
    return _first_row(sql, year, month)


def general_currency(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_currency_breakdown"))

    sql = f"""
        select
            currency,
            count(*) filter (where not is_fraud) as legitimate_count,
            count(*) filter (where is_fraud) as flagged_count
        from {EVENTS}
        where {{window_clause}}
        group by currency
        order by count(*) desc
    """
    return _records(sql, year, month)


def general_top_users(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_top_users_fraud"))

    sql = f"""
        with user_totals as (
            select
                user_id,
                count(*) filter (where is_fraud) as fraud_count,
                coalesce(sum(amount_usd) filter (where is_fraud), 0) as fraud_amount_usd
            from {EVENTS}
            where {{window_clause}}
            group by user_id
            having count(*) filter (where is_fraud) > 0
        )
        select user_id, fraud_count, fraud_amount_usd
        from user_totals
        order by fraud_count desc, fraud_amount_usd desc
        limit 15
    """
    return _records(sql, year, month)


def general_merchants_by_count(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_merchant_fraud_by_count"))

    sql = f"""
        select
            merchant_id,
            count(*) filter (where is_fraud) as fraud_count,
            round(coalesce(sum(amount_usd) filter (where is_fraud), 0), 2) as fraud_amount_usd
        from {EVENTS}
        where {{window_clause}}
        group by merchant_id
        having count(*) filter (where is_fraud) > 0
        order by fraud_count desc
        limit 15
    """
    return _records(sql, year, month)


def general_merchants_by_rate(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_merchant_fraud_by_rate"))

    sql = f"""
        select
            merchant_id,
            count(*) as total_tx,
            count(*) filter (where is_fraud) as fraud_count,
            round(
                count(*) filter (where is_fraud) * 100.0 / nullif(count(*), 0),
                2,
            ) as fraud_rate_pct
        from {EVENTS}
        where {{window_clause}}
        group by merchant_id
        having count(*) >= 3
        order by fraud_rate_pct desc
        limit 15
    """
    return _records(sql, year, month)


def general_countries_by_count(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_country_fraud_count"))

    sql = f"""
        select country, count(*) filter (where is_fraud) as fraud_count
        from {EVENTS}
        where {{window_clause}}
        group by country
        having count(*) filter (where is_fraud) > 0
        order by fraud_count desc
        limit 15
    """
    return _records(sql, year, month)


def general_countries_by_rate(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_country_fraud_rate"))

    sql = f"""
        select
            country,
            count(*) as total_tx,
            count(*) filter (where is_fraud) as fraud_count,
            round(
                count(*) filter (where is_fraud) * 100.0 / nullif(count(*), 0),
                2,
            ) as fraud_rate_pct
        from {EVENTS}
        where {{window_clause}}
        group by country
        having count(*) >= 3
        order by fraud_rate_pct desc
        limit 15
    """
    return _records(sql, year, month)


def general_flag_reasons(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_flag_reasons"))

    excluded = ", ".join(f"'{value}'" for value in FLAG_REASON_EXCLUSIONS)
    sql = f"""
        select reason.value as reason, count(*) as reason_count
        from {EVENTS} as e
        cross join lateral jsonb_array_elements_text(e.flag_reasons) as reason(value)
        where e.is_fraud = true
          and {{window_clause}}
          and reason.value not in ({excluded})
        group by reason.value
        order by reason_count desc
    """
    return _records(sql, year, month)


def velocity_kpis(year: int | None = None, month: int | None = None) -> dict | None:
    if year is None:
        return marts.df_first_row(marts.load_mart("mart_velocity_kpis"))

    sql = f"""
        select
            count(*) filter (where is_velocity_fraud and is_fraud) as velocity_fraud_count,
            round(
                count(*) filter (where is_velocity_fraud and is_fraud) * 100.0
                / nullif(count(*) filter (where is_fraud), 0),
                2
            ) as velocity_fraud_share_pct,
            round(
                coalesce(sum(amount_usd) filter (where is_velocity_fraud and is_fraud), 0),
                2
            ) as sum_velocity_fraud_amount_usd,
            round(
                avg(seconds_since_prev_txn) filter (
                    where is_velocity_fraud
                      and is_fraud
                      and seconds_since_prev_txn is not null
                )::numeric,
                1
            ) as avg_time_between_flagged_sec,
            count(distinct user_id) filter (
                where is_velocity_fraud and is_fraud
            ) as unique_velocity_users
        from {EVENTS}
        where {{window_clause}}
    """
    return _first_row(sql, year, month)


def velocity_buckets(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_velocity_buckets"))

    sql = f"""
        with bucketed as (
            select
                case
                    when seconds_since_prev_txn is null then 'unknown'
                    when seconds_since_prev_txn <= 5 then '0-5s'
                    when seconds_since_prev_txn <= 15 then '6-15s'
                    when seconds_since_prev_txn <= 30 then '16-30s'
                    when seconds_since_prev_txn <= 60 then '31-60s'
                    else '60s+'
                end as velocity_bucket,
                count(*) as fraud_count
            from {VELOCITY_EVENTS}
            where {{window_clause}}
            group by 1
        )
        select velocity_bucket, fraud_count
        from bucketed
        where velocity_bucket != 'unknown'
        order by
            case velocity_bucket
                when '0-5s' then 1
                when '6-15s' then 2
                when '16-30s' then 3
                when '31-60s' then 4
                when '60s+' then 5
                else 6
            end
    """
    return _records(sql, year, month)


def velocity_top_users(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_top_users_velocity"))

    sql = f"""
        select
            user_id,
            count(*) as velocity_fraud_count,
            coalesce(sum(amount_usd), 0) as velocity_fraud_amount_usd,
            round(avg(seconds_since_prev_txn)::numeric, 1) as avg_velocity_seconds
        from {VELOCITY_EVENTS}
        where {{window_clause}}
        group by user_id
        order by velocity_fraud_count desc, velocity_fraud_amount_usd desc
        limit 15
    """
    return _records(sql, year, month)


def velocity_countries_by_count(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_country_velocity_count"))

    sql = f"""
        select country, count(*) as velocity_fraud_count
        from {VELOCITY_EVENTS}
        where {{window_clause}}
        group by country
        order by velocity_fraud_count desc
        limit 15
    """
    return _records(sql, year, month)


def velocity_countries_by_rate(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_country_velocity_rate"))

    sql = f"""
        select
            country,
            count(*) as total_tx,
            count(*) as velocity_fraud_count,
            round(count(*) * 100.0 / nullif(count(*), 0), 2) as velocity_fraud_rate_pct
        from {VELOCITY_EVENTS}
        where {{window_clause}}
        group by country
        having count(*) >= 3
        order by velocity_fraud_rate_pct desc
        limit 15
    """
    return _records(sql, year, month)


def velocity_scatter(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_velocity_scatter"))

    sql = f"""
        select
            transaction_id,
            user_id,
            country,
            amount_usd,
            seconds_since_prev_txn as velocity_seconds
        from {VELOCITY_EVENTS}
        where {{window_clause}}
          and seconds_since_prev_txn is not null
    """
    return _records(sql, year, month)


def velocity_heatmap(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_velocity_heatmap"))

    sql = f"""
        select
            hour_of_day,
            day_of_week,
            count(*) as velocity_fraud_count
        from {VELOCITY_EVENTS}
        where {{window_clause}}
        group by hour_of_day, day_of_week
        order by day_of_week, hour_of_day
    """
    return _records(sql, year, month)


def velocity_repeat_interval(year: int | None = None, month: int | None = None) -> list[dict]:
    if year is None:
        return marts.df_to_records(marts.load_mart("mart_repeat_interval"))

    sql = f"""
        with bucketed as (
            select
                case
                    when repeat_interval_seconds < 1 then '0-1s'
                    when repeat_interval_seconds < 2 then '1-2s'
                    when repeat_interval_seconds < 3 then '2-3s'
                    when repeat_interval_seconds < 4 then '3-4s'
                    when repeat_interval_seconds < 5 then '4-5s'
                    when repeat_interval_seconds < 10 then '5-10s'
                    when repeat_interval_seconds < 30 then '10-30s'
                    when repeat_interval_seconds < 60 then '30-60s'
                    when repeat_interval_seconds < 300 then '1-5m'
                    else '5m+'
                end as interval_bucket,
                count(*) as interval_count
            from {VELOCITY_INTERVALS}
            where {{window_clause}}
            group by 1
        )
        select interval_bucket, interval_count
        from bucketed
        order by
            case interval_bucket
                when '0-1s' then 1
                when '1-2s' then 2
                when '2-3s' then 3
                when '3-4s' then 4
                when '4-5s' then 5
                when '5-10s' then 6
                when '10-30s' then 7
                when '30-60s' then 8
                when '1-5m' then 9
                else 10
            end
    """
    return _records(sql, year, month)
