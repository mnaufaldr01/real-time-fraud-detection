select
    country as origin_country,
    ip_country as destination_country,
    count(*) as txn_count
from {{ ref('int_velocity_fraud_events') }}
where event_at >= current_timestamp - interval '30 days'
  and country is not null
  and ip_country is not null
group by country, ip_country
having count(*) >= 1
order by txn_count desc
limit 30
