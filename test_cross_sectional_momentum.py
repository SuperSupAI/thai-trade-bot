#!/usr/bin/env python
"""
Cross-sectional price-momentum (มาตรา 3.1 ของ "151 Trading Strategies") -- ต่างจาก E4 เดิมที่ใช้
"absolute trend" (ราคาตัวเองเทียบ EMA ของตัวเอง) เป็น "relative momentum": จัดอันดับหุ้นทั้งจักรวาล
ตามผลตอบแทนสะสม 12 เดือน (skip เดือนล่าสุดกันสัญญาณ mean-reversion ระยะสั้น) เลือกซื้อเฉพาะ top N
ที่แข็งแกร่งที่สุดเทียบเพื่อน ถือ 1 เดือน แล้ว rebalance ใหม่ (long-only, ไม่ short เหมือนตำราต้นฉบับ)

เช็คความเสถียรด้วย TRAIN/VALID/TEST ตั้งแต่แรก (บทเรียนจาก hard-cap ที่ผ่านมา)
"""
import pickle
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_hardcap_positions import sim_hardcap
from test_entry_variants import add_extra_signals
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 1_000_000
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
FORMATION = 252   # ~12 เดือนเทรด
SKIP = 21         # ~1 เดือน skip period
REBAL = 21        # rebalance ทุก ~1 เดือน
TOP_N = 10


def sim_cross_sectional_momentum(prep, syms_order, test_dates, top_n, capital_thb=CAPITAL_THB):
    capital_usd = capital_thb / THB_PER_USD
    cash = capital_usd
    positions = {}  # sym -> qty
    trades_count, wins = 0, 0
    entry_prices = {}

    rebal_dates = test_dates[::REBAL]

    for dt in rebal_dates:
        # 1) คำนวณ cumulative return 12 เดือน (skip 1 เดือนล่าสุด) ของหุ้นทุกตัว ณ วันนี้
        scores = []
        for sym in syms_order:
            P = prep[sym]
            close = P["close"]
            if dt not in close.index:
                continue
            i = close.index.get_loc(dt)
            if i < FORMATION:
                continue
            p_now_skip = close.iloc[i - SKIP]
            p_formation_start = close.iloc[i - FORMATION]
            if p_formation_start <= 0:
                continue
            cum_ret = p_now_skip / p_formation_start - 1
            scores.append((sym, cum_ret))

        scores.sort(key=lambda x: x[1], reverse=True)
        target_syms = set(s for s, _ in scores[:top_n])

        # 2) ขายตัวที่ไม่ติด top_n อีกแล้ว
        for sym in list(positions):
            if sym not in target_syms:
                P = prep[sym]
                if dt in P["close"].index:
                    price = float(P["close"].loc[dt])
                    cash += positions[sym] * price * (1 - FEE)
                    trades_count += 1
                    if price > entry_prices[sym]:
                        wins += 1
                    del positions[sym]
                    del entry_prices[sym]

        # 3) ซื้อตัวใหม่ที่ติด top_n แต่ยังไม่ถือ, งบเท่ากันต่อไม้จากเงินสดที่มี
        new_syms = [s for s in target_syms if s not in positions]
        if new_syms:
            budget_each = cash / len(new_syms)
            for sym in new_syms:
                P = prep[sym]
                if dt not in P["close"].index:
                    continue
                price = float(P["close"].loc[dt])
                qty = int((budget_each * (1 - FEE)) / price)
                if qty < 1:
                    continue
                cash -= qty * price * (1 + FEE)
                positions[sym] = qty
                entry_prices[sym] = price

    # ปิดที่เหลือ ณ วันสุดท้าย
    last_dt = test_dates[-1]
    val = cash
    for sym, qty in positions.items():
        P = prep[sym]
        series = P["close"]
        px = float(series.loc[last_dt]) if last_dt in series.index else float(series.iloc[-1])
        val += qty * px
    ret_pct = (val / capital_usd - 1) * 100
    wr = (wins / trades_count * 100) if trades_count else float("nan")
    return dict(ret_pct=round(ret_pct, 1), trades=trades_count, wr=round(wr, 1))


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    n = len(all_dates)

    train_dates = all_dates[: int(n * 0.6)]
    valid_dates = all_dates[int(n * 0.6): int(n * 0.8)]
    test_dates_ = all_dates[int(n * 0.8):]

    print(f"ทั้งชุด: {all_dates[0].date()} -> {all_dates[-1].date()}")
    print(f"TRAIN: {train_dates[0].date()} -> {train_dates[-1].date()}")
    print(f"VALID: {valid_dates[0].date()} -> {valid_dates[-1].date()}")
    print(f"TEST : {test_dates_[0].date()} -> {test_dates_[-1].date()}")
    print(f"ทุนก้อนเดียวรีเซ็ตใหม่ทุกช่วง {CAPITAL_THB:,} บาท, top_n={TOP_N}, rebalance ทุก {REBAL} วัน\n")

    rows = []
    print("=" * 100)
    print(f"{'top_n':>6s}  {'ALL 10 ปี':>26s}  {'TRAIN':>26s}  {'VALID':>26s}  {'TEST':>26s}")
    print("=" * 100)
    for top_n in [5, 10, 20]:
        m_all = sim_cross_sectional_momentum(prep, syms_order, all_dates, top_n)
        m_train = sim_cross_sectional_momentum(prep, syms_order, train_dates, top_n)
        m_valid = sim_cross_sectional_momentum(prep, syms_order, valid_dates, top_n)
        m_test = sim_cross_sectional_momentum(prep, syms_order, test_dates_, top_n)

        def fmt(m):
            return f"{m['ret_pct']:+7.1f}% (n={m['trades']:3d},WR{m['wr']:5.1f}%)"

        print(f"{top_n:>6d}  {fmt(m_all):>26s}  {fmt(m_train):>26s}  {fmt(m_valid):>26s}  {fmt(m_test):>26s}")
        for period, m in [("ALL", m_all), ("TRAIN", m_train), ("VALID", m_valid), ("TEST", m_test)]:
            rows.append(dict(top_n=top_n, period=period, **m))

    # เทียบกับ E4+ExitF hard-cap เดิม (baseline ที่ดีที่สุดที่เจอมาจนถึงตอนนี้)
    print("\n=== เทียบกับ E4+ExitF hard-cap (baseline เดิม) ===")
    for cap in [3, 20]:
        m_all = sim_hardcap(prep, syms_order, all_dates, max_positions=cap, capital_thb=CAPITAL_THB)
        m_train = sim_hardcap(prep, syms_order, train_dates, max_positions=cap, capital_thb=CAPITAL_THB)
        m_valid = sim_hardcap(prep, syms_order, valid_dates, max_positions=cap, capital_thb=CAPITAL_THB)
        m_test = sim_hardcap(prep, syms_order, test_dates_, max_positions=cap, capital_thb=CAPITAL_THB)

        def fmt(m):
            return f"{m['ret_pct']:+7.1f}% (n={m['trades']:3d},WR{m['wr']:5.1f}%)"

        print(f"hardcap={cap:>3d}  {fmt(m_all):>26s}  {fmt(m_train):>26s}  {fmt(m_valid):>26s}  {fmt(m_test):>26s}")
        for period, m in [("ALL", m_all), ("TRAIN", m_train), ("VALID", m_valid), ("TEST", m_test)]:
            rows.append(dict(top_n=f"hardcap{cap}", period=period, **m))

    pd.DataFrame(rows).to_csv("cross_sectional_momentum_results.csv", index=False)
    print("\nบันทึกไว้ที่ cross_sectional_momentum_results.csv")


if __name__ == "__main__":
    main()
