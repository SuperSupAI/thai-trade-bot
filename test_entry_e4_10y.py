#!/usr/bin/env python
"""เอา E4 (Close>EMA200 อย่างเดียว, ชนะสุดตอน 1 ปี +21.3%) ไปเทส 10 ปีเต็ม เทียบ SPY/baseline"""
import pickle
import sys
import pandas as pd

sys.path.insert(0, ".")
import test_exit_optimization as teo
from test_entry_variants import sim_entry, add_extra_signals
from universe import US_STOCKS

CACHE_FILE = "us_close_10y_cache.pkl"
CAPITAL_THB = 100_000

KNOWN = {
    "SPY Buy & Hold": 315.3,
    "E3 TrendMACD (baseline)": 227.4,
    "C) 50%@+10%+breakeven+ratchet": 240.6,
}


def main():
    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)
    print(f"ใช้ cache เดิม: {len(data)} หุ้น")
    prep = teo.precompute(data)
    prep = add_extra_signals(prep)
    syms_order = [s for s in US_STOCKS if s in prep]
    exits = teo.build_exit_grid()
    xcfg = exits["TP12/SL15"]

    all_dates = sorted(set().union(*[P["close"].index for P in prep.values()]))
    print(f"ช่วงทดสอบเต็ม: {all_dates[0].date()} → {all_dates[-1].date()} ({len(all_dates)} วันเทรด)\n")

    for k, v in KNOWN.items():
        print(f"{k:38s} → {v:+7.1f}%  (ผลเดิม)")

    m = sim_entry(prep, syms_order, all_dates, "E4_Simple200", xcfg, rank_by_momentum=False, capital_thb=CAPITAL_THB)
    print(f"{'E4 Simple (Close>EMA200)':38s} → {m['ret_pct']:+7.1f}%  ·  ไม้ {m['trades']:5d}  ·  win rate {m['wr']:5.1f}%")

    final_thb = CAPITAL_THB * (1 + m["ret_pct"] / 100)
    print(f"\nมูลค่าสุดท้าย E4: {final_thb:,.0f} บาท (เทียบ SPY 415,317 บาท)")


if __name__ == "__main__":
    main()
