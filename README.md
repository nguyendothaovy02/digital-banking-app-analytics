# Digital Banking App Analytics
### Onboarding Funnel · Feature Adoption · Churn Risk

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-SQLite-003B57?logo=sqlite&logoColor=white)
![PowerBI](https://img.shields.io/badge/Power_BI-Dashboard-F2C811?logo=powerbi&logoColor=black)
![Status](https://img.shields.io/badge/Status-In_Progress-orange)

---

## Overview

This project simulates a **product analytics workflow for a Vietnamese retail banking app**, covering the full journey from user acquisition to churn risk prediction.

The analysis answers three core business questions:

> 1. Where do users drop off during onboarding — and which acquisition channels bring the highest-quality users?
> 2. Which product features drive long-term engagement and retention?
> 3. Which behavioral signals predict churn, and how should the product/CRM team act on them?

---

## Why Synthetic Data?

Real mobile banking event logs are not publicly available due to **privacy regulations and security constraints** (think: PCI-DSS, SBV data governance requirements in Vietnam).

This dataset was **intentionally designed** to simulate realistic user journeys in a Vietnamese retail banking app, including:
- Multi-step onboarding funnel with realistic drop-off rates
- eKYC approval and failure behavior by acquisition channel
- Feature adoption across transfer, QR payment, bill payment, savings, card, and loan
- Transaction patterns and failure signals
- 30-day and 60-day activity/churn labels

> ⚠️ This dataset does not represent any specific bank's actual performance. All data is assumption-based simulation for analytical demonstration purposes.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Data Generation | Python (pandas, numpy) |
| Data Storage & Queries | SQL (SQLite) |
| Dashboard | Power BI |

---

## Dataset Schema

### `users` — 5,000 rows
| Column | Description |
|---|---|
| `user_id` | Unique user identifier |
| `age_group` | 18-24 / 25-34 / 35-44 / 45-54 / 55+ |
| `city_tier` | Tier 1 (HN/HCM) / Tier 2 / Tier 3 |
| `income_band` | Low / Mid / High |
| `acquisition_channel` | Organic / Referral / Paid Ads / Partnership / Branch |
| `device_os` | Android / iOS |
| `registration_date` | Date of first app registration |

### `app_events` — ~28,000 rows
| Column | Description |
|---|---|
| `user_id` | Foreign key to users |
| `event_time` | Timestamp of the event |
| `event_name` | e.g. `app_install`, `ekyc_complete`, `transfer_initiated` |
| `session_id` | Session identifier |
| `status` | `success` / `failed` |

### `transactions` — ~10,500 rows
| Column | Description |
|---|---|
| `user_id` | Foreign key to users |
| `txn_date` | Transaction timestamp |
| `txn_type` | transfer / qr_payment / bill_payment / savings_deposit / card_payment / loan_repayment |
| `amount_vnd` | Transaction amount in VND |
| `status` | `success` / `failed` |

### `churn_labels` — 5,000 rows
| Column | Description |
|---|---|
| `user_id` | Foreign key to users |
| `is_active_d30` | Boolean — active 30 days post-activation? |
| `is_active_d60` | Boolean — active 60 days post-activation? |
| `churn_flag` | True if not active at D60 |

---

## Designed Behavioral Patterns

The dataset was engineered to embed **6 realistic behavioral patterns** — each one maps to a concrete business insight:

| # | Pattern | Business Insight |
|---|---|---|
| P1 | Referral/Organic activation rate (44–45%) is 2× higher than Paid Ads (23%) | Channel quality matters more than acquisition volume |
| P2 | eKYC is the largest single drop-off point: 69% start → 46% complete | Clear onboarding pain point → actionable product fix |
| P3 | Users with first transaction ≤7 days have 83% D30 retention vs 22% for later | Speed-to-value is the strongest early retention predictor |
| P4 | Users adopting ≥2 features have 48% churn rate vs 99% for 0-feature users | Feature breadth creates product stickiness |
| P5 | Bill payment / savings users retain at 80% D30 vs 11% for others | Recurring and savings behavior = deeper banking engagement |
| P6 | Users with ≥3 failed transactions have 73% churn rate | Friction (failed txns, login errors) is a leading churn signal |

---

## Project Structure

```
digital-banking-app-analytics/
│
├── data/
│   ├── users.csv
│   ├── app_events.csv
│   ├── transactions.csv
│   └── churn_labels.csv
│
├── generate_data.py        # Synthetic data generation with pattern logic
├── analysis.sql            # SQL queries for all 4 dashboard views
├── banking_analytics.pbix  # Power BI dashboard (4 pages)
└── README.md
```

---

## Dashboard Pages (Power BI)

| Page | Key Metrics |
|---|---|
| **Executive Summary** | Total users, activation rate, D30 retention, churn rate, avg transactions/user |
| **Onboarding Funnel** | Step-by-step funnel conversion by channel, OS, age group |
| **Feature Adoption** | Adoption rate per feature; feature × retention heatmap |
| **Retention & Churn** | Cohort retention curves, churn-risk segments, recommended CRM actions |

---

## Key Findings

- **eKYC is the #1 onboarding bottleneck** — only 46% of users who start eKYC complete it. Simplifying document upload or offering live agent support could recover ~23% of drop-offs.
- **Referral channel delivers the highest LTV signal** — 2× activation rate and higher D30 retention vs Paid Ads. Referral incentive programs have strong ROI potential.
- **The 7-day activation window is critical** — users who transact within 7 days of activation are 3.7× more likely to still be active at D30. This defines the key onboarding success milestone.
- **Multi-feature adoption is the strongest retention lever** — moving users from 1 feature to ≥2 features cuts churn by ~22pp. Cross-sell nudges (e.g., "Pay your bills here") during onboarding have measurable impact.
- **Failed transactions are an early warning signal** — users with ≥3 failures churn at 73%. Real-time intervention (push notification, support contact) at the 2nd failure could reduce churn meaningfully.

---

## How to Run

```bash
# 1. Clone the repo
git clone https://github.com/nguyendothaovy02/digital-banking-app-analytics.git
cd digital-banking-app-analytics

# 2. Install dependencies
pip install pandas numpy

# 3. Generate the dataset
python generate_data.py
# → Creates 4 CSV files in /data

# 4. Run SQL analysis
# Load the CSVs into SQLite or any SQL client, then run analysis.sql
```

---

## About This Project

Built as a portfolio project to demonstrate end-to-end data analytics skills applied to the **digital banking / fintech domain** — including event-level data modeling, product funnel analysis, retention cohort analysis, and churn risk segmentation.

Background context: prior experience in **mobile app analytics** (Firebase/GA4, cohort analysis, ROAS, retention) for gaming/consumer apps — this project applies the same analytical framework to the retail banking context.
