-- ============================================================
-- Digital Banking App Analytics — SQL Analysis
-- Database: SQLite (banking.db)
-- ============================================================


-- ============================================================
-- PAGE 1: EXECUTIVE SUMMARY
-- ============================================================

-- Query 1: Top-line KPIs
SELECT
    (SELECT COUNT(DISTINCT user_id) FROM users) AS total_users,

    ROUND(100.0 *
        (SELECT COUNT(DISTINCT user_id) FROM app_events
         WHERE event_name = 'account_activated' AND status = 'success')
        / (SELECT COUNT(DISTINCT user_id) FROM users), 1
    ) AS activation_rate_pct,

    ROUND(100.0 *
        (SELECT SUM(is_active_d30) FROM churn_labels)
        / (SELECT COUNT(DISTINCT user_id) FROM users), 1
    ) AS d30_retention_pct,

    ROUND(100.0 *
        (SELECT SUM(churn_flag) FROM churn_labels)
        / (SELECT COUNT(DISTINCT user_id) FROM users), 1
    ) AS churn_rate_pct;


-- ============================================================
-- PAGE 2: ONBOARDING FUNNEL
-- ============================================================

-- Query 2: Funnel step conversion — overall
-- Pattern P2: eKYC là bước drop-off lớn nhất
SELECT
    event_name,
    COUNT(DISTINCT user_id)  AS users_reached,
    ROUND(
        100.0 * COUNT(DISTINCT user_id)
        / (SELECT COUNT(DISTINCT user_id) FROM app_events
           WHERE event_name = 'app_install'), 1
    ) AS pct_of_installs
FROM app_events
WHERE event_name IN (
    'app_install', 'register_start', 'register_complete',
    'ekyc_start', 'ekyc_complete', 'account_activated'
)
AND status = 'success'
GROUP BY event_name
ORDER BY
    CASE event_name
        WHEN 'app_install'       THEN 1
        WHEN 'register_start'    THEN 2
        WHEN 'register_complete' THEN 3
        WHEN 'ekyc_start'        THEN 4
        WHEN 'ekyc_complete'     THEN 5
        WHEN 'account_activated' THEN 6
    END;


-- Query 3: Activation rate by acquisition channel
-- Pattern P1: Referral/Organic activation rate cao hơn Paid Ads
SELECT
    u.acquisition_channel,
    COUNT(DISTINCT u.user_id)  AS total_users,
    COUNT(DISTINCT CASE WHEN e.event_name = 'account_activated'
                         AND e.status = 'success'
                        THEN e.user_id END)  AS activated_users,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN e.event_name = 'account_activated'
                                     AND e.status = 'success'
                                    THEN e.user_id END)
        / COUNT(DISTINCT u.user_id), 1
    )  AS activation_rate_pct
FROM users u
LEFT JOIN app_events e ON u.user_id = e.user_id
GROUP BY u.acquisition_channel
ORDER BY activation_rate_pct DESC;


-- ============================================================
-- PAGE 3: FEATURE ADOPTION
-- ============================================================

-- Query 4: D30 retention by first transaction timing
-- Pattern P3: First txn trong 7 ngày → D30 retention cao hơn
WITH first_txn AS (
    SELECT
        user_id,
        MIN(txn_date) AS first_txn_date
    FROM transactions
    WHERE status = 'success'
    GROUP BY user_id
),
activation AS (
    SELECT
        user_id,
        MIN(event_time) AS activation_date
    FROM app_events
    WHERE event_name = 'account_activated' AND status = 'success'
    GROUP BY user_id
),
user_speed AS (
    SELECT
        a.user_id,
        CAST(
            (JULIANDAY(f.first_txn_date) - JULIANDAY(a.activation_date))
        AS INTEGER) AS days_to_first_txn
    FROM activation a
    LEFT JOIN first_txn f ON a.user_id = f.user_id
)
SELECT
    CASE
        WHEN days_to_first_txn IS NULL THEN 'No transaction'
        WHEN days_to_first_txn <= 7    THEN 'Within 7 days'
        ELSE 'After 7 days'
    END                                          AS txn_timing,
    COUNT(*)                                     AS users,
    ROUND(100.0 * SUM(cl.is_active_d30)
          / COUNT(*), 1)                         AS d30_retention_pct
FROM user_speed us
JOIN churn_labels cl ON us.user_id = cl.user_id
GROUP BY txn_timing
ORDER BY d30_retention_pct DESC;


-- Query 5: Feature adoption rate (among activated users)
WITH activated_users AS (
    SELECT DISTINCT user_id
    FROM app_events
    WHERE event_name = 'account_activated' AND status = 'success'
)
SELECT
    event_name                            AS feature,
    COUNT(DISTINCT user_id)               AS users_adopted,
    ROUND(
        100.0 * COUNT(DISTINCT user_id)
        / (SELECT COUNT(*) FROM activated_users), 1
    )                                     AS adoption_rate_pct
FROM app_events
WHERE event_name IN (
    'transfer_initiated', 'qr_payment', 'bill_payment',
    'savings_opened', 'card_payment', 'loan_viewed'
)
AND status = 'success'
AND user_id IN (SELECT user_id FROM activated_users)
GROUP BY event_name
ORDER BY adoption_rate_pct DESC;


-- Query 6: D30 retention by feature segment
-- Pattern P4: ≥2 features → churn thấp hơn
-- Pattern P5: Bill/Savings users retain tốt hơn
WITH activated_users AS (
    SELECT DISTINCT user_id
    FROM app_events
    WHERE event_name = 'account_activated' AND status = 'success'
),
user_features AS (
    SELECT
        user_id,
        COUNT(DISTINCT event_name)                                      AS n_features,
        MAX(CASE WHEN event_name = 'bill_payment'   THEN 1 ELSE 0 END) AS uses_bill,
        MAX(CASE WHEN event_name = 'savings_opened' THEN 1 ELSE 0 END) AS uses_savings
    FROM app_events
    WHERE event_name IN (
        'transfer_initiated', 'qr_payment', 'bill_payment',
        'savings_opened', 'card_payment', 'loan_viewed'
    )
    AND status = 'success'
    AND user_id IN (SELECT user_id FROM activated_users)
    GROUP BY user_id
)
SELECT
    CASE
        WHEN uf.uses_bill = 1 OR uf.uses_savings = 1 THEN 'Bill/Savings user'
        WHEN uf.n_features >= 2                       THEN 'Multi-feature (no bill/savings)'
        WHEN uf.n_features = 1                        THEN 'Single feature'
        ELSE 'No feature used'
    END                                               AS user_segment,
    COUNT(*)                                          AS users,
    ROUND(100.0 * SUM(cl.is_active_d30) / COUNT(*), 1) AS d30_retention_pct
FROM activated_users au
LEFT JOIN user_features uf ON au.user_id = uf.user_id
LEFT JOIN churn_labels  cl ON au.user_id = cl.user_id
GROUP BY user_segment
ORDER BY d30_retention_pct DESC;


-- ============================================================
-- PAGE 4: RETENTION & CHURN
-- ============================================================

-- Query 7: Churn rate by failed transaction count
-- Pattern P6: Failed transactions nhiều → churn risk cao
WITH user_failed_txn AS (
    SELECT
        user_id,
        COUNT(*) AS failed_txns
    FROM transactions
    WHERE status = 'failed'
    GROUP BY user_id
)
SELECT
    CASE
        WHEN ft.failed_txns IS NULL THEN '0 failed'
        WHEN ft.failed_txns <= 2   THEN '1-2 failed'
        ELSE '3+ failed'
    END                                               AS fail_bucket,
    COUNT(*)                                          AS users,
    ROUND(100.0 * SUM(cl.churn_flag) / COUNT(*), 1)  AS churn_rate_pct
FROM churn_labels cl
LEFT JOIN user_failed_txn ft ON cl.user_id = ft.user_id
GROUP BY fail_bucket
ORDER BY churn_rate_pct DESC;


-- Query 8: Cohort retention by registration month
SELECT
    STRFTIME('%Y-%m', registration_date)        AS cohort_month,
    COUNT(DISTINCT u.user_id)                   AS cohort_size,
    ROUND(100.0 * SUM(cl.is_active_d30)
          / COUNT(DISTINCT u.user_id), 1)       AS d30_retention_pct,
    ROUND(100.0 * SUM(cl.is_active_d60)
          / COUNT(DISTINCT u.user_id), 1)       AS d60_retention_pct
FROM users u
LEFT JOIN churn_labels cl ON u.user_id = cl.user_id
GROUP BY cohort_month
ORDER BY cohort_month;