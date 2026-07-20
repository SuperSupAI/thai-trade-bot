#!/usr/bin/env python
"""
ต่อยอด cross-sectional momentum: (1) เช็คเฉพาะปี 2022 (ตลาดหมีจริง, Fed ขึ้นดอกเบี้ยแรง) ตามธรรมเนียม
stress test ของโปรเจกต์นี้ (2) ลองใส่ hard stop-loss -20% ระหว่างเดือน (ไม่ต้องรอ rebalance รายเดือน)
ดูว่าช่วยจำกัดความเสียหายจากการกระจุกตัวแค่ 5 ตัวได้ไหม
"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import add_extra_signals
from universe import US_STOCKS
from test_cross_sectional_momentum import FORMATION, SKIP, REBAL, sim_cross_sectional_momentum

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 1_000_000
THB_PER_USD = teo.THB_PER_USD
FEE = teo.FEE
HARD_SL = 0.20


def sim_cross_sectional_momentum_sl(prep, syms_order, test_dates, top_n, capital_thb=CAPITAL_THB):
    """เหมือนเดิมทุกอย่าง แต่เช็ค hard stop-loss -20% ได้ทุกวัน ไม่ต้องรอ rebalance รายเดือน"""
    capital_usd = capital_thb / THB_PER_USD
    cash = capital_usd
    positions = {}
    entry_prices = {}
    trades_count, wins = 0, 0
    rebal_dates = set(test_dates[::REBAL])

    for dt in test_dates:
        for sym in list(positions):
            P = prep[sym]
            if dt not in P["close"].index:
                continue
            price = float(P["close"].loc[dt])
            chg = price / entry_prices[sym] - 1
            if chg <= -HARD_SL:
                cash += positions[sym] * price * (1 - FEE)
                trades_count += 1
                del positions[sym]
                del entry_prices[sym]

        if dt not in rebal_dates:
            continue

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
            scores.append((sym, p_now_skip / p_formation_start - 1))
        scores.sort(key=lambda x: x[1], reverse=True)
        target_syms = set(s for s, _ in scores[:top_n])

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

    last_dt = test_dates[-1]
    val = cash
    for sym, qty in positions.items():
        series = prep[sym]["close"]
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

    dates_2022 = [d for d in all_dates if d.year == 2022]
    print(f"ปี 2022 เต็มปี: {dates_2022[0].date()} -> {dates_2022[-1].date()} ({len(dates_2022)} วัน)")
    print(f"ทุน {CAPITAL_THB:,} บาท\n")

    print("=== เฉพาะปี 2022 (bear market stress test) ===")
    rows = []
    for top_n in [5, 10, 20]:
        m = sim_cross_sectional_momentum(prep, syms_order, dates_2022, top_n)
        print(f"top_n={top_n:2d} (ไม่มี stop-loss ระหว่างทาง): {m['ret_pct']:+7.1f}%  ไม้ {m['trades']:3d}  WR {m['wr']:5.1f}%")
        rows.append(dict(test="2022_only_no_sl", top_n=top_n, **m))

    print("\n=== เฉพาะปี 2022 + hard stop-loss -20% ระหว่างทาง ===")
    for top_n in [5, 10, 20]:
        m = sim_cross_sectional_momentum_sl(prep, syms_order, dates_2022, top_n)
        print(f"top_n={top_n:2d} (มี stop-loss -20%):         {m['ret_pct']:+7.1f}%  ไม้ {m['trades']:3d}  WR {m['wr']:5.1f}%")
        rows.append(dict(test="2022_only_with_sl", top_n=top_n, **m))

    print("\n=== เต็ม 10 ปี + hard stop-loss -20% ระหว่างทาง (เทียบไม่มี SL เดิม) ===")
    for top_n in [5, 10, 20]:
        m_nosl = sim_cross_sectional_momentum(prep, syms_order, all_dates, top_n)
        m_sl = sim_cross_sectional_momentum_sl(prep, syms_order, all_dates, top_n)
        print(f"top_n={top_n:2d}  ไม่มี SL: {m_nosl['ret_pct']:+8.1f}% (ไม้{m_nosl['trades']:3d})   "
              f"มี SL -20%: {m_sl['ret_pct']:+8.1f}% (ไม้{m_sl['trades']:3d})")
        rows.append(dict(test="all10y_no_sl", top_n=top_n, **m_nosl))
        rows.append(dict(test="all10y_with_sl", top_n=top_n, **m_sl))

    pd.DataFrame(rows).to_csv("cross_sectional_momentum_stress_results.csv", index=False)
    print("\nบันทึกไว้ที่ cross_sectional_momentum_stress_results.csv")


if __name__ == "__main__":
    main()
