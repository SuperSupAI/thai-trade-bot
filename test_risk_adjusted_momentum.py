#!/usr/bin/env python
"""
ทดสอบ risk-adjusted momentum (R_risk.adj = ผลตอบแทนเฉลี่ยรายวันช่วง formation / ความผันผวนรายวันช่วงเดียวกัน
-- เหมือน Sharpe ratio ของช่วง formation) เทียบกับ cumulative momentum เดิม (แค่ผลตอบแทนสะสมเฉยๆ)
ใช้ daily returns แทน monthly แบบตำราต้นฉบับ (ข้อมูลเรามีรายวัน ไม่ใช่รายเดือน) -- adaptation ที่พบได้ทั่วไป
ในทางปฏิบัติ ให้คะแนนสูงกับหุ้นที่ "วิ่งแรงแบบนิ่งๆ" มากกว่าหุ้นที่วิ่งแรงแบบแกว่งสุดขั้ว
"""
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from test_cross_sectional_momentum_dr_universe import DR_COVERED

FORMATION, SKIP, REBAL = 252, 21, 21
CAPITAL_THB = 1_000_000
DR_RATIO = 0.01


def sim_momentum(price_lookup, syms_order, test_dates, top_n, score_fn, capital_thb, fee, thb_per_usd=None, dr_ratio=1.0):
    capital_base = capital_thb / thb_per_usd if thb_per_usd else capital_thb
    cash = capital_base
    positions = {}
    trades_count, wins = 0, 0
    entry_px = {}
    rebal_dates = test_dates[::REBAL]

    for dt in rebal_dates:
        scores = []
        for sym in syms_order:
            close = price_lookup[sym]
            if dt not in close.index:
                continue
            i = close.index.get_loc(dt)
            if i < FORMATION:
                continue
            sc = score_fn(close, i)
            if sc is None:
                continue
            scores.append((sym, sc))
        scores.sort(key=lambda x: x[1], reverse=True)
        target = set(s for s, _ in scores[:top_n])

        for sym in list(positions):
            if sym not in target:
                close = price_lookup[sym]
                if dt in close.index:
                    price = float(close.loc[dt]) * dr_ratio
                    cash += positions[sym] * price * (1 - fee)
                    trades_count += 1
                    if price > entry_px[sym]:
                        wins += 1
                    del positions[sym]

        new_syms = [s for s in target if s not in positions]
        if new_syms:
            budget_each = cash / len(new_syms)
            for sym in new_syms:
                close = price_lookup[sym]
                if dt not in close.index:
                    continue
                price = float(close.loc[dt]) * dr_ratio
                qty = int((budget_each * (1 - fee)) / price)
                if qty < 1:
                    continue
                cash -= qty * price * (1 + fee)
                positions[sym] = qty
                entry_px[sym] = price

    last_dt = test_dates[-1]
    val = cash
    for sym, qty in positions.items():
        close = price_lookup[sym]
        px = float(close.loc[last_dt]) * dr_ratio if last_dt in close.index else float(close.iloc[-1]) * dr_ratio
        val += qty * px
    ret_pct = (val / capital_base - 1) * 100
    wr = (wins / trades_count * 100) if trades_count else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades_count, wr=round(wr, 1))


def score_cumulative(close, i):
    p_now = close.iloc[i - SKIP]
    p_start = close.iloc[i - FORMATION]
    if p_start <= 0:
        return None
    return p_now / p_start - 1


def score_risk_adjusted(close, i):
    window = close.iloc[i - FORMATION: i - SKIP]
    daily_rets = window.pct_change().dropna()
    if len(daily_rets) < 30:
        return None
    std = daily_rets.std()
    if std == 0 or pd.isna(std):
        return None
    return daily_rets.mean() / std


def run_universe(name, price_lookup, syms_order, thb_per_usd, dr_ratio, fee, top_ns):
    all_dates = sorted(set().union(*[price_lookup[s].index for s in syms_order]))
    n = len(all_dates)
    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates_ = all_dates[int(n * 0.8):]

    print(f"\n{'='*100}")
    print(f"{name}")
    print(f"{'='*100}")
    rows = []
    for top_n in top_ns:
        for score_name, score_fn in [("Cumulative (เดิม)", score_cumulative), ("Risk-adjusted (Sharpe-style)", score_risk_adjusted)]:
            m_all = sim_momentum(price_lookup, syms_order, all_dates, top_n, score_fn, CAPITAL_THB, fee, thb_per_usd, dr_ratio)
            m_train = sim_momentum(price_lookup, syms_order, train_dates, top_n, score_fn, CAPITAL_THB, fee, thb_per_usd, dr_ratio)
            m_valid = sim_momentum(price_lookup, syms_order, valid_dates, top_n, score_fn, CAPITAL_THB, fee, thb_per_usd, dr_ratio)
            m_test = sim_momentum(price_lookup, syms_order, test_dates_, top_n, score_fn, CAPITAL_THB, fee, thb_per_usd, dr_ratio)

            def fmt(m):
                return f"{m['ret_pct']:+7.1f}%(WR{m['wr']:5.1f}%)"

            print(f"top_n={top_n} {score_name:30s}  ALL:{fmt(m_all):>20s}  TRAIN:{fmt(m_train):>20s}  "
                  f"VALID:{fmt(m_valid):>20s}  TEST:{fmt(m_test):>20s}")
            for period, m in [("ALL", m_all), ("TRAIN", m_train), ("VALID", m_valid), ("TEST", m_test)]:
                rows.append(dict(universe=name, top_n=top_n, score=score_name, period=period, **m))
    return rows


def main():
    all_rows = []
    with open("us_close_10y_cache.pkl", "rb") as f:
        us_data = pickle.load(f)
    prep = teo.precompute(us_data)
    prep = add_extra_signals(prep)
    dr_syms = [s for s in DR_COVERED if s in prep]
    dr_price_lookup = {s: prep[s]["close"] for s in dr_syms}
    all_rows += run_universe("DR universe (21 mega-cap สหรัฐฯ)", dr_price_lookup, dr_syms,
                              thb_per_usd=teo.THB_PER_USD, dr_ratio=DR_RATIO, fee=teo.FEE, top_ns=[3, 5])

    with open("thai_stocks_10y_cache.pkl", "rb") as f:
        thai_data = pickle.load(f)
    thai_syms = sorted(thai_data.keys())
    all_rows += run_universe("หุ้นไทย (75 ตัว)", thai_data, thai_syms,
                              thb_per_usd=None, dr_ratio=1.0, fee=0.002, top_ns=[3, 5])

    pd.DataFrame(all_rows).to_csv("risk_adjusted_momentum_results.csv", index=False)
    print("\nบันทึกไว้ที่ risk_adjusted_momentum_results.csv")


if __name__ == "__main__":
    main()
