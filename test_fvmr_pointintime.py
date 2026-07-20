#!/usr/bin/env python
"""
FVMR แบบแก้ look-ahead bias จริง -- ใช้ข้อมูลงบจาก SEC EDGAR (sec_edgar_fundamentals.py) ซึ่งมีวันที่
"ยื่นจริง" (filed) ติดมาด้วย ดังนั้น F (ROE, EBIT margin) และ V (P/E) และ R (EPS growth) ทุกตัวคำนวณจาก
ข้อมูลที่ "รู้ได้จริง ณ เวลานั้น" เท่านั้น ไม่ใช่ค่าปัจจุบันคงที่แบบ test_fvmr.py เดิม
M (Momentum) เหมือนเดิม (คำนวณ point-in-time อยู่แล้วตั้งแต่ต้น)
"""
import json
import os
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from universe import US_STOCKS

FACTS_DIR = "sec_facts_cache"
PRICE_CACHE = "us_close_10y_cache.pkl"
FEE = 0.002


def load_facts(sym):
    path = os.path.join(FACTS_DIR, f"{sym}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def value_asof(series, asof_date):
    """หาค่าล่าสุดที่ 'ยื่นแล้ว' (filed <= asof_date) จาก series ของ concept เดียว -- คืน (val, end_date) หรือ None"""
    candidates = [e for e in series if e["filed"] <= asof_date]
    if not candidates:
        return None
    best = max(candidates, key=lambda e: e["end"])
    return best["val"], best["end"]


def prior_year_value(series, current_end):
    """หาค่าปีก่อนหน้า (end ประมาณ 1 ปีก่อน current_end) สำหรับคำนวณ growth"""
    cur = pd.Timestamp(current_end)
    best, best_gap = None, None
    for e in series:
        end = pd.Timestamp(e["end"])
        gap_days = (cur - end).days
        if 300 <= gap_days <= 430:
            if best_gap is None or abs(gap_days - 365) < abs(best_gap - 365):
                best, best_gap = e["val"], gap_days
    return best


def score_asof(facts, price, asof_date_str):
    rev = value_asof(facts.get("Revenues", []), asof_date_str)
    ni = value_asof(facts.get("NetIncomeLoss", []), asof_date_str)
    eq = value_asof(facts.get("StockholdersEquity", []), asof_date_str)
    opinc = value_asof(facts.get("OperatingIncomeLoss", []), asof_date_str)
    eps = value_asof(facts.get("EarningsPerShareDiluted", []), asof_date_str)
    if not (rev and ni and eq and opinc and eps):
        return None

    roe = ni[0] / eq[0] if eq[0] else None
    ebit_margin = opinc[0] / rev[0] if rev[0] else None
    pe = price / eps[0] if eps[0] and eps[0] > 0 else None

    eps_series = facts.get("EarningsPerShareDiluted", [])
    prior_eps = prior_year_value(eps_series, eps[1])
    eps_growth = None
    if prior_eps is not None and prior_eps != 0:
        eps_growth = (eps[0] - prior_eps) / abs(prior_eps)

    if roe is None or ebit_margin is None:
        return None

    f_score = (1 if roe > 0.15 else 0) + (1 if ebit_margin > 0.10 else 0)
    v_score = (1 if (pe is not None and 0 < pe < 15) else 0) + (1 if (pe is not None and 0 < pe < 25) else 0)
    r_score = (1 if (eps_growth is not None and eps_growth > 0.05) else 0) * 2
    return dict(f=f_score, v=v_score, r=r_score, roe=roe, ebit_margin=ebit_margin, pe=pe, eps_growth=eps_growth)


def main():
    with open(PRICE_CACHE, "rb") as f:
        price_data = pickle.load(f)

    rows = []
    n_ok = 0
    for sym in US_STOCKS:
        facts = load_facts(sym)
        if not facts or sym not in price_data:
            continue
        close = price_data[sym]
        n = len(close)
        step, lookback = 63, 126
        got_any = False
        for i in range(lookback, n - step, step):
            dt = close.index[i]
            asof_str = dt.strftime("%Y-%m-%d")
            price = float(close.iloc[i])
            sc = score_asof(facts, price, asof_str)
            if sc is None:
                continue
            mom_ret = float(close.iloc[i] / close.iloc[i - lookback] - 1)
            fwd_ret = float(close.iloc[i + step] / close.iloc[i] - 1) - 2 * FEE
            rows.append(dict(symbol=sym, date=dt, mom_ret=mom_ret, fwd_ret=fwd_ret,
                              f=sc["f"], v=sc["v"], r=sc["r"]))
            got_any = True
        if got_any:
            n_ok += 1

    df = pd.DataFrame(rows)
    print(f"ใช้ได้ {n_ok}/{len(US_STOCKS)} หุ้น (มีทั้งราคา + งบ SEC ที่ parse ได้), รวม {len(df)} หุ้น-ไตรมาส\n")
    if df.empty:
        print("ไม่มีข้อมูลพอ -- เช็คว่า sec_edgar_fundamentals.py ดึงเสร็จหรือยัง")
        return

    df["mom_tercile"] = pd.qcut(df["mom_ret"], 3, labels=["low", "mid", "high"], duplicates="drop")
    df["fvr_total"] = df["f"] + df["v"] + df["r"]
    m_map = {"low": 0, "mid": 1, "high": 2}
    mom_numeric = df["mom_tercile"].astype(str).map(m_map).astype(int)
    df["total_score"] = df["fvr_total"] + mom_numeric

    q_lo, q_hi = df["total_score"].quantile([0.33, 0.67])
    top = df[df["total_score"] >= q_hi]
    bot = df[df["total_score"] <= q_lo]

    def stats(d, label):
        wr = (d["fwd_ret"] > 0).mean() * 100
        avg = d["fwd_ret"].mean() * 100
        print(f"{label}: n={len(d)}, win rate (forward 3m บวก)={wr:.1f}%, avg forward return={avg:.2f}%")

    print(f"คะแนนรวม FVMR แบบ point-in-time จริง (F+V+M+R, เต็ม 8): เส้นแบ่ง top>={q_hi:.1f}, bottom<={q_lo:.1f}")
    stats(top, "Top tercile (FVMR สูง)")
    stats(bot, "Bottom tercile (FVMR ต่ำ)")
    print(f"\nค่าเฉลี่ยทั้งชุด: n={len(df)}, win rate={(df['fwd_ret']>0).mean()*100:.1f}%, avg={df['fwd_ret'].mean()*100:.2f}%")

    df.to_csv("fvmr_us_pointintime_snapshots.csv", index=False)
    print("\nบันทึกไว้ที่ fvmr_us_pointintime_snapshots.csv")


if __name__ == "__main__":
    main()
