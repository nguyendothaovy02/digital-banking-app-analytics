"""
Digital Banking App Analytics — Synthetic Data Generator
=========================================================
Script này generate 4 bảng CSV:
  1. users.csv          — thông tin user
  2. app_events.csv     — event log kiểu Firebase/GA4
  3. transactions.csv   — lịch sử giao dịch
  4. churn_labels.csv   — nhãn active/churn sau 30 & 60 ngày

6 PATTERNS được design CÓ CHỦ ĐÍCH vào data:
  P1: Referral/Organic có activation rate cao hơn Paid Ads
  P2: eKYC là bước drop-off lớn nhất trong onboarding funnel
  P3: First transaction trong 7 ngày → D30 retention cao hơn
  P4: User dùng ≥2 features → churn thấp hơn
  P5: Bill payment/Savings users giữ lại lâu hơn QR-only users
  P6: Failed transactions nhiều → churn risk cao hơn
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# ============================================================
# CẤU HÌNH CHUNG
# ============================================================
SEED = 42
np.random.seed(SEED)
random.seed(SEED)

N_USERS = 5000          # tổng số user
START_DATE = datetime(2024, 1, 1)
END_DATE   = datetime(2024, 6, 30)
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def random_date(start, end):
    """Trả về datetime ngẫu nhiên trong khoảng [start, end]."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

# ============================================================
# BẢNG 1: USERS
# ============================================================
print("Generating users...")

age_groups       = ["18-24", "25-34", "35-44", "45-54", "55+"]
city_tiers       = ["Tier 1", "Tier 2", "Tier 3"]   # HN/HCM=T1, Da Nang/Can Tho=T2, other=T3
income_bands     = ["Low", "Mid", "High"]
acq_channels     = ["Organic", "Referral", "Paid Ads", "Partnership", "Branch"]
device_os        = ["Android", "iOS"]

# Tỷ lệ phân phối thực tế VN banking app
channel_weights  = [0.25, 0.20, 0.30, 0.15, 0.10]   # Paid Ads nhiều nhất
os_weights       = [0.68, 0.32]                        # Android dominant ở VN

users = pd.DataFrame({
    "user_id": [f"U{str(i).zfill(5)}" for i in range(1, N_USERS + 1)],
    "age_group": np.random.choice(age_groups, N_USERS, p=[0.30, 0.35, 0.20, 0.10, 0.05]),
    "city_tier": np.random.choice(city_tiers, N_USERS, p=[0.45, 0.35, 0.20]),
    "income_band": np.random.choice(income_bands, N_USERS, p=[0.30, 0.50, 0.20]),
    "acquisition_channel": np.random.choice(acq_channels, N_USERS, p=channel_weights),
    "device_os": np.random.choice(device_os, N_USERS, p=os_weights),
    "registration_date": [random_date(START_DATE, END_DATE - timedelta(days=65))
                          for _ in range(N_USERS)],
})

users.to_csv(f"{OUTPUT_DIR}/users.csv", index=False)
print(f"  → {len(users)} users saved.")

# ============================================================
# HÀM HỖ TRỢ: TÍNH XÁC SUẤT THEO PATTERN
# ============================================================

def get_kyc_pass_prob(channel):
    """
    PATTERN P1 + P2:
    - Referral/Organic pass eKYC cao hơn (user chất lượng)
    - eKYC vẫn là drop-off lớn nhất (tất cả đều thấp hơn bước trước)
    """
    probs = {
        "Organic":     0.72,
        "Referral":    0.78,   # cao nhất
        "Paid Ads":    0.55,   # thấp nhất — P1
        "Partnership": 0.65,
        "Branch":      0.70,
    }
    return probs.get(channel, 0.65)

def get_activation_prob(channel, kyc_passed):
    """
    PATTERN P1: Referral/Organic activation cao hơn Paid Ads.
    Activation = bước sau eKYC.
    """
    if not kyc_passed:
        return 0.0
    probs = {
        "Organic":     0.80,
        "Referral":    0.85,   # tốt nhất
        "Paid Ads":    0.62,   # kém nhất
        "Partnership": 0.75,
        "Branch":      0.78,
    }
    return probs.get(channel, 0.75)

# ============================================================
# BẢNG 2: APP EVENTS
# ============================================================
print("Generating app_events...")

events_rows = []
# Lưu thông tin từng user để dùng cho bảng transactions và churn
user_meta = {}

onboarding_steps = ["app_install", "register_start", "register_complete",
                    "ekyc_start", "ekyc_complete", "account_activated"]

feature_events = ["transfer_initiated", "qr_payment", "bill_payment",
                  "savings_opened", "card_payment", "loan_viewed"]

for _, user in users.iterrows():
    uid       = user["user_id"]
    reg_date  = pd.Timestamp(user["registration_date"])
    channel   = user["acquisition_channel"]

    meta = {
        "activated": False,
        "activation_date": None,
        "features_used": set(),
        "failed_txn_count": 0,
        "first_txn_days": None,   # số ngày từ activation đến first transaction
    }

    # --- ONBOARDING FUNNEL ---
    # Mỗi bước có xác suất drop-off riêng
    current_time = reg_date + timedelta(hours=random.randint(0, 2))
    step_passed  = True

    drop_probs = {
        "app_install":        1.00,   # tất cả đều có
        "register_start":     0.92,   # 8% bounce ngay
        "register_complete":  0.85,   # 15% drop khi điền form
        "ekyc_start":         0.90,   # trong số đã register
        "ekyc_complete":      get_kyc_pass_prob(channel),   # P2: drop lớn nhất
        "account_activated":  get_activation_prob(channel, True),
    }

    for step in onboarding_steps:
        if not step_passed:
            break

        # Xác suất pass bước này
        prob = drop_probs[step]

        # ekyc_complete dùng prob riêng dựa vào channel (đã tính ở trên)
        pass_this = random.random() < prob

        # Tạo event bất kể pass hay fail (có status)
        status = "success" if pass_this else "failed"
        events_rows.append({
            "user_id":    uid,
            "event_time": current_time + timedelta(minutes=random.randint(1, 30)),
            "event_name": step,
            "session_id": f"S{uid}_{step[:4]}",
            "status":     status,
        })

        if not pass_this:
            step_passed = False
        else:
            current_time += timedelta(hours=random.randint(1, 12))
            if step == "account_activated":
                meta["activated"] = True
                meta["activation_date"] = current_time

    # --- FEATURE USAGE (chỉ user đã activated) ---
    if meta["activated"]:
        act_date = meta["activation_date"]

        # PATTERN P4: chọn số features dùng — phân phối có chủ đích
        # User giữ lại (chưa churn) sẽ dùng nhiều feature hơn
        # Ta sẽ làm ngược lại: set số feature ảnh hưởng churn label sau
        n_features = np.random.choice([0, 1, 2, 3, 4, 5], p=[0.10, 0.25, 0.28, 0.20, 0.12, 0.05])
        chosen_features = random.sample(feature_events, min(n_features, len(feature_events)))

        meta["features_used"] = set(chosen_features)

        for feat in chosen_features:
            feat_time = act_date + timedelta(days=random.randint(1, 45),
                                              hours=random.randint(0, 23))
            events_rows.append({
                "user_id":    uid,
                "event_time": feat_time,
                "event_name": feat,
                "session_id": f"S{uid}_{feat[:4]}",
                "status":     "success",
            })

    user_meta[uid] = meta

app_events = pd.DataFrame(events_rows)
app_events["event_time"] = pd.to_datetime(app_events["event_time"])
app_events = app_events.sort_values(["user_id", "event_time"]).reset_index(drop=True)

app_events.to_csv(f"{OUTPUT_DIR}/app_events.csv", index=False)
print(f"  → {len(app_events)} events saved.")

# ============================================================
# BẢNG 3: TRANSACTIONS
# ============================================================
print("Generating transactions...")

txn_types  = ["transfer", "qr_payment", "bill_payment", "savings_deposit",
              "card_payment", "loan_repayment"]
txn_rows   = []

for _, user in users.iterrows():
    uid  = user["user_id"]
    meta = user_meta[uid]

    if not meta["activated"]:
        continue

    act_date     = meta["activation_date"]
    features     = meta["features_used"]
    income_band  = user["income_band"]

    # Số transactions tương ứng với độ engaged
    base_txns    = max(0, int(np.random.normal(loc=len(features) * 3, scale=3)))

    # Amount theo income band
    amount_range = {
        "Low":  (50_000,  2_000_000),
        "Mid":  (100_000, 10_000_000),
        "High": (500_000, 50_000_000),
    }
    lo, hi = amount_range[income_band]

    first_txn_done = False
    failed_count   = 0

    for i in range(base_txns):
        # Thời gian transaction
        txn_date = act_date + timedelta(days=random.randint(0, 60),
                                         hours=random.randint(6, 22))

        # Type: ưu tiên feature đã dùng
        if features and random.random() < 0.70:
            # map feature event → txn type
            feat_to_txn = {
                "transfer_initiated": "transfer",
                "qr_payment":         "qr_payment",
                "bill_payment":       "bill_payment",
                "savings_opened":     "savings_deposit",
                "card_payment":       "card_payment",
                "loan_viewed":        "loan_repayment",
            }
            feat_choice = random.choice(list(features))
            txn_type    = feat_to_txn.get(feat_choice, "transfer")
        else:
            txn_type = random.choice(txn_types)

        # PATTERN P6: user churn-risk có nhiều failed transactions hơn
        # Tạm thời set fail rate 8%; sẽ tăng cho user churn khi label
        fail_rate = 0.08
        status    = "failed" if random.random() < fail_rate else "success"
        if status == "failed":
            failed_count += 1

        amount = random.randint(lo // 1000, hi // 1000) * 1000

        # Ghi nhớ first transaction timing (PATTERN P3)
        if status == "success" and not first_txn_done:
            days_to_first = (txn_date - act_date).days
            meta["first_txn_days"] = days_to_first
            first_txn_done = True

        txn_rows.append({
            "user_id":   uid,
            "txn_date":  txn_date,
            "txn_type":  txn_type,
            "amount_vnd": amount,
            "status":    status,
        })

    meta["failed_txn_count"] = failed_count
    user_meta[uid] = meta

transactions = pd.DataFrame(txn_rows)
transactions["txn_date"] = pd.to_datetime(transactions["txn_date"])
transactions = transactions.sort_values(["user_id", "txn_date"]).reset_index(drop=True)

transactions.to_csv(f"{OUTPUT_DIR}/transactions.csv", index=False)
print(f"  → {len(transactions)} transactions saved.")

# ============================================================
# BẢNG 4: CHURN LABELS
# ============================================================
print("Generating churn_labels...")

churn_rows = []

for _, user in users.iterrows():
    uid     = user["user_id"]
    meta    = user_meta[uid]

    if not meta["activated"]:
        # User chưa activated → churn ngay
        churn_rows.append({
            "user_id":       uid,
            "is_active_d30": False,
            "is_active_d60": False,
            "churn_flag":    True,
        })
        continue

    features      = meta["features_used"]
    failed_txns   = meta["failed_txn_count"]
    first_txn_d   = meta["first_txn_days"]   # None nếu chưa có txn
    channel       = user["acquisition_channel"]

    # Base probability: "sẽ còn active sau 30 ngày?"
    p_active_d30 = 0.60   # baseline

    # PATTERN P1: Referral/Organic retain tốt hơn
    if channel in ("Referral", "Organic"):
        p_active_d30 += 0.10
    elif channel == "Paid Ads":
        p_active_d30 -= 0.10

    # PATTERN P3: First txn trong 7 ngày → D30 retention cao hơn
    if first_txn_d is not None and first_txn_d <= 7:
        p_active_d30 += 0.15
    elif first_txn_d is None:
        p_active_d30 -= 0.20   # không có transaction → churn risk cao

    # PATTERN P4: ≥2 features → ít churn hơn
    n_feat = len(features)
    if n_feat >= 2:
        p_active_d30 += 0.10
    elif n_feat == 0:
        p_active_d30 -= 0.15

    # PATTERN P5: Bill payment hoặc savings → retain tốt hơn
    if "bill_payment" in features or "savings_opened" in features:
        p_active_d30 += 0.08

    # PATTERN P6: Nhiều failed txn → churn risk cao
    if failed_txns >= 3:
        p_active_d30 -= 0.15
    elif failed_txns >= 1:
        p_active_d30 -= 0.05

    # Clamp xác suất trong [0.05, 0.95]
    p_active_d30 = max(0.05, min(0.95, p_active_d30))

    # D60 thấp hơn D30 một chút
    p_active_d60 = p_active_d30 * 0.82

    is_active_d30 = random.random() < p_active_d30
    is_active_d60 = random.random() < p_active_d60 if is_active_d30 else False

    churn_rows.append({
        "user_id":       uid,
        "is_active_d30": is_active_d30,
        "is_active_d60": is_active_d60,
        "churn_flag":    not is_active_d60,
    })

churn_labels = pd.DataFrame(churn_rows)
churn_labels.to_csv(f"{OUTPUT_DIR}/churn_labels.csv", index=False)
print(f"  → {len(churn_labels)} churn labels saved.")

# ============================================================
# QUICK SANITY CHECK — in ra để verify patterns
# ============================================================
print("\n" + "="*55)
print("SANITY CHECK — Verify 6 Patterns")
print("="*55)

# Merge để kiểm tra
df = users.merge(churn_labels, on="user_id")
activated = df[df["user_id"].isin([u for u, m in user_meta.items() if m["activated"]])]

# P1: Channel vs Activation rate
print("\n[P1] Activation rate by channel:")
act_flags = {uid: meta["activated"] for uid, meta in user_meta.items()}
users["activated"] = users["user_id"].map(act_flags)
print(users.groupby("acquisition_channel")["activated"].mean().sort_values(ascending=False).round(3))

# P2: eKYC drop-off
print("\n[P2] Onboarding funnel conversion:")
funnel_steps = ["app_install", "register_start", "register_complete",
                "ekyc_start", "ekyc_complete", "account_activated"]
for step in funnel_steps:
    n = app_events[(app_events["event_name"] == step) & (app_events["status"] == "success")]["user_id"].nunique()
    print(f"  {step:<22}: {n:>5} users  ({n/N_USERS*100:.1f}%)")

# P3: First txn timing vs D30 retention
print("\n[P3] D30 retention by first-txn timing:")
first_txn_map = {uid: meta["first_txn_days"] for uid, meta in user_meta.items()}
df["first_txn_days"] = df["user_id"].map(first_txn_map)
df["first_txn_bucket"] = df["first_txn_days"].apply(
    lambda x: "≤7 days" if (x is not None and x <= 7)
    else (">7 days" if x is not None else "No txn"))
print(df.groupby("first_txn_bucket")["is_active_d30"].mean().round(3))

# P4: Feature count vs churn
print("\n[P4] Churn rate by number of features used:")
feat_count_map = {uid: len(meta["features_used"]) for uid, meta in user_meta.items()}
df["n_features"] = df["user_id"].map(feat_count_map)
df["n_feat_bucket"] = df["n_features"].apply(lambda x: "0" if x==0 else ("1" if x==1 else "≥2"))
print(df.groupby("n_feat_bucket")["churn_flag"].mean().round(3))

# P5: Bill/savings vs retention
print("\n[P5] D30 retention: bill/savings users vs others:")
def has_recurring(uid):
    feats = user_meta[uid]["features_used"]
    return "bill_payment" in feats or "savings_opened" in feats
df["has_recurring"] = df["user_id"].apply(has_recurring)
print(df.groupby("has_recurring")["is_active_d30"].mean().round(3))

# P6: Failed txn vs churn
print("\n[P6] Churn rate by failed transaction count:")
df["failed_txns"] = df["user_id"].map({uid: meta["failed_txn_count"] for uid, meta in user_meta.items()})
df["fail_bucket"] = df["failed_txns"].apply(lambda x: "0" if x==0 else ("1-2" if x<=2 else "≥3"))
print(df.groupby("fail_bucket")["churn_flag"].mean().round(3))

print("\n✅ Done! Files saved to ./data/")
print("   users.csv | app_events.csv | transactions.csv | churn_labels.csv")
