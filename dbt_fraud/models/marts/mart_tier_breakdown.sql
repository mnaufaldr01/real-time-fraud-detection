select
    risk_tier,
    count(*) as tier_count,
    round(count(*) * 100.0 / nullif(sum(count(*)) over (), 0), 2) as tier_pct
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
group by risk_tier
order by tier_count desc
